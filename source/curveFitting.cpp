#include "curveFitting.h"

#include <maya/MAngle.h>
#include <maya/MDistance.h>
#include <maya/MTypes.h>
#include <algorithm>
#include <cmath>
#include <limits>
#include <set>
#include <vector>

namespace KeyReducerDetail
{
struct CurveSample
{
    MTime time;
    double value;
};

struct HandleFit
{
    bool enabled = false;
    double outX = 0.0, outY = 0.0, inX = 0.0, inY = 0.0;
    double error = 0.0;
};

struct Removal
{
    MTime time;
    HandleFit handles;
};

enum class Strategy { Native, Frozen, Fitted };

struct FitResult
{
    Strategy strategy = Strategy::Native;
    std::vector<Removal> removals;
    double error = 0.0;
};

CurveLocks captureLocks(const MFnAnimCurve &curve)
{
    CurveLocks locks;
    for (unsigned int index = 0; index < curve.numKeys(); ++index)
    {
        locks.tangents.push_back(curve.tangentsLocked(index));
        locks.weights.push_back(curve.weightsLocked(index));
    }
    return locks;
}

MStatus restoreLocks(MFnAnimCurve &curve, const CurveLocks &locks)
{
    if (curve.numKeys() != locks.tangents.size() || curve.numKeys() != locks.weights.size())
        return MS::kFailure;
    // Maya does not consistently record these flags in MAnimCurveChange.
    // Set only the flags that differ, after restoring the key geometry.
    for (unsigned int index = 0; index < curve.numKeys(); ++index)
    {
        if (curve.tangentsLocked(index) != locks.tangents[index])
        {
            MStatus status = curve.setTangentsLocked(index, locks.tangents[index]);
            if (!status) return status;
        }
        if (curve.weightsLocked(index) != locks.weights[index])
        {
            MStatus status = curve.setWeightsLocked(index, locks.weights[index]);
            if (!status) return status;
        }
    }
    return MS::kSuccess;
}

static bool stepped(MFnAnimCurve::TangentType type)
{
    return type == MFnAnimCurve::kTangentStep || type == MFnAnimCurve::kTangentStepNext;
}

static double displayValueScale(const MFnAnimCurve &curve)
{
    switch (curve.animCurveType())
    {
    case MFnAnimCurve::kAnimCurveTA:
        return MAngle(1.0, MAngle::kRadians).as(MAngle::uiUnit());
    case MFnAnimCurve::kAnimCurveTL:
        return MDistance(1.0, MDistance::kCentimeters).as(MDistance::uiUnit());
    case MFnAnimCurve::kAnimCurveTT:
        return MTime(1.0, MTime::kSeconds).as(MTime::uiUnit());
    default:
        return 1.0;
    }
}

static std::vector<CurveSample> sampleReference(const MFnAnimCurve &curve)
{
    std::set<MTime> times;
    for (unsigned int index = 0; index < curve.numKeys(); ++index)
    {
        const MTime begin = curve.time(index);
        times.insert(begin);
        if (index + 1 == curve.numKeys())
            break;
        const MTime end = curve.time(index + 1);
        const double first = begin.as(MTime::kSeconds);
        const double duration = end.as(MTime::kSeconds) - first;
        const double frames = end.as(MTime::uiUnit()) - begin.as(MTime::uiUnit());
        const int steps = static_cast<int>(std::max(8.0, std::min(64.0, std::ceil(frames * 8.0))));
        for (int step = 1; step < steps; ++step)
            times.insert(MTime(first + duration * step / steps, MTime::kSeconds));
        times.insert(MTime(first + duration / 1024.0, MTime::kSeconds));
        times.insert(MTime(first + duration * 1023.0 / 1024.0, MTime::kSeconds));
    }
    std::vector<CurveSample> samples;
    samples.reserve(times.size());
    for (const MTime &time : times)
        samples.push_back(CurveSample{time, curve.evaluate(time)});
    return samples;
}

static double maxError(const MFnAnimCurve &curve, const std::vector<CurveSample> &reference,
                       double scale, double stopAt, const MTime &begin, const MTime &end)
{
    double error = 0.0;
    for (const CurveSample &sample : reference)
    {
        MStatus status;
        const double value = curve.evaluate(sample.time, &status);
        if (!status || !std::isfinite(value))
            return std::numeric_limits<double>::infinity();
        const double difference = std::fabs(value - sample.value) * scale;
        // Changing a boundary's automatic slope must not reshape spans outside
        // the requested range. Only native evaluation round-off is permitted.
        if ((sample.time < begin || sample.time > end) && difference > 1.0e-6)
            return std::numeric_limits<double>::infinity();
        error = std::max(error, difference);
        if (error > stopAt)
            break;
    }
    return error;
}

static MStatus freezeTangents(MFnAnimCurve &curve, const MTime &begin, const MTime &end,
                              MAnimCurveChange &change)
{
    for (unsigned int index = 0; index < curve.numKeys(); ++index)
    {
        const MTime time = curve.time(index);
        if (time < begin || time > end)
            continue;
        // Capture evaluated handles before changing either type. Tangent labels
        // are free, but discontinuous interpolation must not become continuous.
        const auto inType = curve.inTangentType(index);
        const auto outType = curve.outTangentType(index);
        if (!stepped(inType))
        {
            MStatus status = curve.setInTangentType(index, MFnAnimCurve::kTangentFixed, &change);
            if (!status) return status;
        }
        if (!stepped(outType))
        {
            MStatus status = curve.setOutTangentType(index, MFnAnimCurve::kTangentFixed, &change);
            if (!status) return status;
        }
    }
    return MS::kSuccess;
}

static MStatus applyHandles(MFnAnimCurve &curve, unsigned int left, const HandleFit &fit,
                            MAnimCurveChange &change)
{
    if (!fit.enabled)
        return MS::kSuccess;
    const unsigned int right = left + 1;
    for (unsigned int index : {left, right})
    {
        MStatus status = curve.setTangentsLocked(index, false, &change);
        if (!status) return status;
        status = curve.setWeightsLocked(index, false, &change);
        if (!status) return status;
    }
    MStatus status = curve.setTangent(left, fit.outX, fit.outY, false, &change, false);
    if (!status) return status;
    return curve.setTangent(right, fit.inX, fit.inY, true, &change, false);
}

// Monotone normalized Bezier time coordinate; the control polygon is ordered.
static double bezierParameter(double time, double outLength, double inLength)
{
    double low = 0.0, high = 1.0;
    for (int iteration = 0; iteration < 36; ++iteration)
    {
        const double u = (low + high) * 0.5;
        const double v = 1.0 - u;
        const double x = 3.0 * v * v * u * outLength +
                         3.0 * v * u * u * (1.0 - inLength) + u * u * u;
        if (x < time) low = u;
        else high = u;
    }
    return (low + high) * 0.5;
}

static HandleFit solveHandles(const MFnAnimCurve &curve, unsigned int left,
                              const std::vector<CurveSample> &reference,
                              double outLength, double inLength)
{
    HandleFit fit;
    const MTime first = curve.time(left), last = curve.time(left + 1);
    const double start = first.as(MTime::kSeconds);
    const double span = last.as(MTime::kSeconds) - start;
    const double y0 = curve.value(left), y1 = curve.value(left + 1);
    const bool weighted = curve.isWeighted();
    double aa = 0.0, ab = 0.0, bb = 0.0, ay = 0.0, by = 0.0;
    for (const CurveSample &sample : reference)
    {
        if (sample.time <= first || sample.time >= last) continue;
        const double t = (sample.time.as(MTime::kSeconds) - start) / span;
        const double u = weighted ? bezierParameter(t, outLength, inLength) : t;
        const double v = 1.0 - u;
        double a, b, base;
        if (weighted)
        {
            a = 3.0 * v * v * u;
            b = -3.0 * v * u * u;
            base = (v * v * v + a) * y0 + (u * u * u - b) * y1;
        }
        else
        {
            a = u * u * u - 2.0 * u * u + u;
            b = u * u * u - u * u;
            base = (2.0 * u * u * u - 3.0 * u * u + 1.0) * y0 +
                   (-2.0 * u * u * u + 3.0 * u * u) * y1;
        }
        const double residual = sample.value - base;
        aa += a * a; ab += a * b; bb += b * b;
        ay += a * residual; by += b * residual;
    }
    const double determinant = aa * bb - ab * ab;
    if (span <= 0.0 || determinant <= 1.0e-14 * std::max(1.0, aa * bb))
        return fit;
    const double outY = (ay * bb - by * ab) / determinant;
    const double inY = (by * aa - ay * ab) / determinant;
    if (!std::isfinite(outY) || !std::isfinite(inY))
        return fit;
    fit.enabled = true;
    // Maya's weighted tangent vectors are three times the control-point delta.
    fit.outX = weighted ? 3.0 * outLength * span : span;
    fit.inX = weighted ? 3.0 * inLength * span : span;
    fit.outY = weighted ? 3.0 * outY : outY;
    fit.inY = weighted ? 3.0 * inY : inY;
    // Rank analytic local fits; final acceptance always uses actual Maya values.
    for (const CurveSample &sample : reference)
    {
        if (sample.time <= first || sample.time >= last) continue;
        const double t = (sample.time.as(MTime::kSeconds) - start) / span;
        const double u = weighted ? bezierParameter(t, outLength, inLength) : t;
        const double v = 1.0 - u;
        const double value = weighted ?
            v * v * v * y0 + 3.0 * v * v * u * (y0 + outY) +
            3.0 * v * u * u * (y1 - inY) + u * u * u * y1 :
            (2.0 * u * u * u - 3.0 * u * u + 1.0) * y0 +
            (-2.0 * u * u * u + 3.0 * u * u) * y1 +
            (u * u * u - 2.0 * u * u + u) * outY + (u * u * u - u * u) * inY;
        fit.error = std::max(fit.error, std::fabs(value - sample.value));
    }
    return fit;
}

static std::vector<HandleFit> fittingCandidates(const MFnAnimCurve &curve, unsigned int left,
                                               const std::vector<CurveSample> &reference)
{
    std::vector<HandleFit> fits;
    if (!curve.isWeighted())
    {
        const HandleFit fit = solveHandles(curve, left, reference, 1.0 / 3.0, 1.0 / 3.0);
        if (fit.enabled) fits.push_back(fit);
        return fits;
    }
    std::vector<double> outLengths{1.0 / 6.0, 1.0 / 3.0, 0.5};
    std::vector<double> inLengths = outLengths;
#if MAYA_API_VERSION >= 20180000
    MFnAnimCurve::TangentValue outX, outY, inX, inY;
#else
    float outX, outY, inX, inY;
#endif
    curve.getTangent(left, outX, outY, false);
    curve.getTangent(left + 1, inX, inY, true);
    const double span = curve.time(left + 1).as(MTime::kSeconds) - curve.time(left).as(MTime::kSeconds);
    outLengths.push_back(std::max(1.0e-4, std::min(0.95, outX / (3.0 * span))));
    inLengths.push_back(std::max(1.0e-4, std::min(0.95, inX / (3.0 * span))));
    for (double outLength : outLengths)
        for (double inLength : inLengths)
        {
            if (outLength + inLength > 1.0) continue;
            const HandleFit fit = solveHandles(curve, left, reference, outLength, inLength);
            if (fit.enabled) fits.push_back(fit);
        }
    std::sort(fits.begin(), fits.end(), [](const HandleFit &a, const HandleFit &b) { return a.error < b.error; });
    if (fits.size() > 3) fits.resize(3);
    return fits;
}

static MStatus reducePass(MFnAnimCurve &curve, const MTime &begin, const MTime &end,
                          const std::vector<CurveSample> &reference, double scale,
                          double tolerance, FitResult &result, MAnimCurveChange &passChange)
{
    if (result.strategy != Strategy::Native)
    {
        MStatus status = freezeTangents(curve, begin, end, passChange);
        if (!status) return status;
    }
    for (unsigned int index = 1; index + 1 < curve.numKeys(); )
    {
        const MTime time = curve.time(index);
        if (time <= begin || time >= end || stepped(curve.outTangentType(index - 1)) ||
            stepped(curve.inTangentType(index)) || stepped(curve.outTangentType(index)))
        {
            ++index;
            continue;
        }
        const CurveLocks trialLocks = captureLocks(curve);
        MAnimCurveChange trial;
        MStatus status = curve.remove(index, &trial);
        if (!status) return status;
        double bestError = maxError(curve, reference, scale, tolerance, begin, end);
        bool accepted = bestError <= tolerance;
        HandleFit bestFit;
        if (!accepted) bestError = tolerance;
        if (result.strategy == Strategy::Fitted && bestError > 1.0e-12)
        {
            const auto fits = fittingCandidates(curve, index - 1, reference);
            for (const HandleFit &fit : fits)
            {
                const CurveLocks tangentLocks = captureLocks(curve);
                MAnimCurveChange tangentTrial;
                status = applyHandles(curve, index - 1, fit, tangentTrial);
                const double error = status ? maxError(curve, reference, scale, bestError, begin, end) :
                                             std::numeric_limits<double>::infinity();
                MStatus restored = tangentTrial.undoIt();
                if (restored) restored = restoreLocks(curve, tangentLocks);
                if (!restored) { trial.undoIt(); return restored; }
                if (error < bestError)
                {
                    accepted = true;
                    bestError = error;
                    bestFit = fit;
                }
            }
        }
        status = trial.undoIt();
        if (status) status = restoreLocks(curve, trialLocks);
        if (!status) return status;
        if (accepted)
        {
            status = curve.remove(index, &passChange);
            if (!status) return status;
            status = applyHandles(curve, index - 1, bestFit, passChange);
            if (!status) return status;
            result.removals.push_back(Removal{time, bestFit});
        }
        else ++index;
    }
    result.error = maxError(curve, reference, scale, std::numeric_limits<double>::infinity(), begin, end);
    return MS::kSuccess;
}

MStatus fitReducedCurve(MFnAnimCurve &curve, const MTime &begin, const MTime &end,
                        double tolerance, MAnimCurveChange &change)
{
    const auto reference = sampleReference(curve);
    const CurveLocks originalLocks = captureLocks(curve);
    const double scale = displayValueScale(curve);
    const double budget = std::max(1.0e-10, tolerance * 0.95);
    FitResult best;
    for (Strategy strategy : {Strategy::Native, Strategy::Frozen, Strategy::Fitted})
    {
        FitResult result;
        result.strategy = strategy;
        MAnimCurveChange trial;
        const MStatus status = reducePass(curve, begin, end, reference, scale, budget, result, trial);
        MStatus restored = trial.undoIt();
        if (restored) restored = restoreLocks(curve, originalLocks);
        if (!restored) return restored;
        if (!status) return status;
        if (result.error <= budget &&
            (result.removals.size() > best.removals.size() ||
             (result.removals.size() == best.removals.size() && result.error < best.error)))
            best = result;
    }
    if (best.removals.empty()) return MS::kSuccess;
    if (best.strategy != Strategy::Native)
    {
        MStatus status = freezeTangents(curve, begin, end, change);
        if (!status) return status;
    }
    for (const Removal &removal : best.removals)
    {
        unsigned int index;
        if (!curve.find(removal.time, index)) return MS::kFailure;
        MStatus status = curve.remove(index, &change);
        if (!status) return status;
        status = applyHandles(curve, index - 1, removal.handles, change);
        if (!status) return status;
    }
    // Replay must satisfy the immutable reference, not the last trial's curve.
    return maxError(curve, reference, scale, std::numeric_limits<double>::infinity(), begin, end) <=
           std::max(1.0e-10, tolerance) ? MS::kSuccess : MS::kFailure;
}
}
