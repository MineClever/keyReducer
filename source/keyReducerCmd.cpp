#include <maya/MSelectionList.h>
#include <maya/MPlugArray.h> 
#include <maya/MPlug.h>
#include <maya/MFnDependencyNode.h>
#include <maya/MAnimControl.h>
#include <cmath>
#include <algorithm>
#include <map>
#include <set>

#include "keyReducerCmd.h"
#include "curveFitting.h"


void* KeyReducerCmd::creator()
{
	return new KeyReducerCmd;
}

KeyReducerCmd::KeyReducerCmd()
{
}

bool KeyReducerCmd::isUndoable() const
{
	return true;
}


MSyntax KeyReducerCmd::syntaxCreator()
{
    MSyntax syntax;
	
	syntax.addFlag("-v", "-value", MSyntax::kDouble);
	syntax.addFlag("-st", "-startTime", MSyntax::kLong);
	syntax.addFlag("-et", "-endTime", MSyntax::kLong);
    syntax.addFlag("-h", "-help", MSyntax::kNoArg);
    syntax.addFlag("-pb", "-preBake", MSyntax::kNoArg);
    syntax.addFlag("-ak", "-alignKeys", MSyntax::kNoArg);
	
	return syntax;
}


MStatus KeyReducerCmd::doIt(const MArgList& args)
{
    MArgDatabase argData(syntax(), args);
    
    if (argData.isFlagSet("-help"))
    {
        MGlobal::displayInfo("This command reduce the keys for the given animated attributes of the selected objects.\n\t args: list fo strings - the list of object attributes to evaluate, i.e. locator1.tx \n\t -value: float - sampled curve-value error tolerance in scene display units. Default: 0.5\n\t -startTime: int - if specified, the keys before this frame will be ignored\n\t -endTime: int - if specified, the keys after this frame will be ignored\n\t -preBake: no arg, if specified the curve will be baked before key reducing, this will remove any broken/weighted tangents from your animation curve.");
        MGlobal::displayInfo("\t-alignKeys (-ak): after reduction, insert missing keys so animated attributes share the union of retained key times within the processing range. Off by default; subframes are preserved.");
        return MS::kSuccess;
    }

    MStatus status = MS::kSuccess;

    MPlugArray plugsList;
    for (unsigned int nth = 0; nth < args.length(); nth++)
    {
        MString inputString = args.asString(nth, &status);
        if (status == MStatus::kFailure)
        {
            MGlobal::displayError("tcKeyReducer error while parsing arguments");
            return status;
        }
        
        MPlug plug;
        MSelectionList selection;
        selection.add(inputString);
        status = selection.getPlug(0, plug);
        if (status != MStatus::kSuccess)
        {
            MGlobal::displayError("tcKeyReducer error while parsing argument. Failed to find plug " + inputString+ ".");
            return status;
        }
        plugsList.append(plug);
    }

    if (plugsList.length() == 0)
	{
		MGlobal::displayError("tcReduceKeys: Please specify at least one attribute.");
		return MS::kFailure;
	}
    
    
    if (argData.isFlagSet("-value"))
		argData.getFlagArgument("-value", 0, deviation);
    else
        deviation = 0.5;
    if (!std::isfinite(deviation) || deviation < 0.0)
    {
        MGlobal::displayError("tcKeyReducer: value must be finite and nonnegative.");
        return MS::kFailure;
    }

    hasStartTime = false;
    hasEndTime = false;
	if (argData.isFlagSet("-startTime"))
    {
        hasStartTime = true;
		argData.getFlagArgument("-startTime", 0, startTime);
    }
	
	if (argData.isFlagSet("-endTime"))
    {
        hasEndTime = true;
		argData.getFlagArgument("-endTime", 0, endTime);
    }
    
    preBake = argData.isFlagSet("-preBake");

    std::vector<MObject> curves;
    for (unsigned int i = 0; i < plugsList.length(); ++i)
	{
        MFnAnimCurve fnCurve(plugsList[i], &status);
        if (!status || !fnCurve.isTimeInput() || fnCurve.numKeys() == 0)
            continue;
        const MObject object = fnCurve.object();
        if (std::find(curves.begin(), curves.end(), object) != curves.end())
            continue;
        curves.push_back(object);
        locksBefore.push_back(CurveLockSnapshot{object, KeyReducerDetail::captureLocks(fnCurve)});
        status = keyReduce(fnCurve);
        if (!status)
        {
            animCurveChange.undoIt();
            restoreCurveLocks(locksBefore);
            return status;
        }
	}

    if (argData.isFlagSet("-alignKeys"))
    {
        status = alignKeyTimes(curves);
        if (!status)
        {
            animCurveChange.undoIt();
            restoreCurveLocks(locksBefore);
            MGlobal::displayError("tcKeyReducer: could not align key times; changes were reverted.");
            return status;
        }
    }
    for (const MObject &object : curves)
    {
        MFnAnimCurve curve(object);
        locksAfter.push_back(CurveLockSnapshot{object, KeyReducerDetail::captureLocks(curve)});
    }
    return MS::kSuccess;
}

MStatus KeyReducerCmd::alignKeyTimes(const std::vector<MObject> &curves)
{
    // Preserve MTime directly: alignment shares times across curves without
    // rounding subframes or assuming a 24 fps timeline.
    std::set<MTime> times;
    for (const MObject &object : curves)
    {
        MFnAnimCurve curve(object);
        for (unsigned int index = 0; index < curve.numKeys(); ++index)
        {
            const MTime time = curve.time(index);
            if (isAfterStartTime(time) && isBeforeEndTime(time))
                times.insert(time);
        }
    }

    for (const MObject &object : curves)
    {
        MFnAnimCurve curve(object);
#if MAYA_API_VERSION < 20190300
        // Capture all missing-key values before any insertion can change the
        // neighboring interpolation in SDKs without shape-preserving insert.
        std::map<MTime, double> values;
        for (const MTime &time : times)
        {
            unsigned int index;
            if (!curve.find(time, index))
            {
                MStatus status;
                const double value = curve.evaluate(time, &status);
                if (!status)
                    return status;
                values[time] = value;
            }
        }
#endif
        for (const MTime &time : times)
        {
            unsigned int index;
            if (curve.find(time, index))
                continue;
            MStatus status;
#if MAYA_API_VERSION >= 20190300
            // SDK insertion preserves the existing curve shape and records
            // both new keys and tangent edits in the command's undo state.
            curve.insertKey(time, false, &animCurveChange, &status);
#else
            // Older SDKs have no insertKey. Sample the reduced curve before
            // adding a key; neighboring interpolation may change on these SDKs.
            const double value = values.find(time)->second;
            curve.addKey(time, value, MFnAnimCurve::kTangentGlobal,
                         MFnAnimCurve::kTangentGlobal, &animCurveChange, &status);
#endif
            if (!status)
                return status;
        }
    }
    return MS::kSuccess;
}

bool KeyReducerCmd::isAfterStartTime(const MTime &time)
{
    if (!hasStartTime)
        return true;
    
    return time.as(MTime::uiUnit()) >= startTime;
}

bool KeyReducerCmd::isBeforeEndTime(const MTime &time)
{
    if (!hasEndTime)
        return true;
    
    return time.as(MTime::uiUnit()) <= endTime;
}

void KeyReducerCmd::sampleCurve(MFnAnimCurve &curve)
{
    int min = hasStartTime? startTime: curve.time(0).as(MTime::uiUnit());
    int max = hasEndTime? endTime: curve.time(curve.numKeys() - 1).as(MTime::uiUnit());
    
    std::vector<double> values;
    values.reserve(int(max - min + 1));
    
    for (double i = min; i <= max ; ++i)
    {
        MTime t(i, MTime::uiUnit());
        values.push_back(curve.evaluate(t));
    }
    
    for (int i = curve.numKeys() - 1; i >= 0 ; --i)
	{
		MTime time = curve.time(i);
		if (isAfterStartTime(time) && isBeforeEndTime(time))
			curve.remove(i, &animCurveChange);
	}
    
    for (double i = min; i <= max ; ++i)
    {
        MTime t(i, MTime::uiUnit());
        curve.addKeyframe(t, values[int(i - min)], &animCurveChange);
    }
}

MStatus KeyReducerCmd::keyReduce(MFnAnimCurve &curve)
{
    if (curve.numKeys() <= 2)
        return MS::kSuccess;
    if (preBake)
    {
        sampleCurve(curve);
        curve.setIsWeighted(false, &animCurveChange);
    }

    std::vector<MTime> eligible;
    for (unsigned int index = 0; index < curve.numKeys(); ++index)
    {
        const MTime time = curve.time(index);
        if (isAfterStartTime(time) && isBeforeEndTime(time))
            eligible.push_back(time);
    }
    if (eligible.size() <= 2)
        return MS::kSuccess;

    return KeyReducerDetail::fitReducedCurve(curve, eligible.front(), eligible.back(),
                                             deviation, animCurveChange);
}

MStatus KeyReducerCmd::redoIt()
{
    const MStatus status = animCurveChange.redoIt();
    return status ? restoreCurveLocks(locksAfter) : status;
}

MStatus KeyReducerCmd::undoIt()
{
    const MStatus status = animCurveChange.undoIt();
    return status ? restoreCurveLocks(locksBefore) : status;
}

MStatus KeyReducerCmd::restoreCurveLocks(const std::vector<CurveLockSnapshot> &snapshots)
{
    for (const CurveLockSnapshot &snapshot : snapshots)
    {
        MStatus status;
        MFnAnimCurve curve(snapshot.curve, &status);
        if (!status) return status;
        status = KeyReducerDetail::restoreLocks(curve, snapshot.locks);
        if (!status) return status;
    }
    return MS::kSuccess;
}

