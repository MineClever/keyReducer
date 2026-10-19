#ifndef KEYREDUCER_CURVE_FITTING_H
#define KEYREDUCER_CURVE_FITTING_H

#include <maya/MFnAnimCurve.h>
#include <maya/MAnimCurveChange.h>
#include <vector>

namespace KeyReducerDetail
{
struct CurveLocks
{
    std::vector<bool> tangents;
    std::vector<bool> weights;
};

CurveLocks captureLocks(const MFnAnimCurve &curve);
MStatus restoreLocks(MFnAnimCurve &curve, const CurveLocks &locks);

// Trial all strategies against one immutable reference and replay the winner
// into the caller's undo record. Output tangent types are unconstrained.
MStatus fitReducedCurve(MFnAnimCurve &curve, const MTime &begin, const MTime &end,
                        double tolerance, MAnimCurveChange &change);
}

#endif
