//
//  keyReducerCmd.h
//  keyReducer
//
//  Created by Daniele Federico on 13/01/15.
//
//

#ifndef keyReducer_keyReducerCmd_h
#define keyReducer_keyReducerCmd_h

#include <maya/MPxCommand.h>
#include <maya/MSyntax.h>
#include <maya/MArgDatabase.h>
#include <maya/MArgList.h>
#include <maya/MGlobal.h>
#include <maya/MAnimCurveChange.h>
#include <maya/MFnAnimCurve.h>

#include <vector>

#include <maya/MTypes.h>
#include "curveFitting.h"


class KeyReducerCmd: public MPxCommand
{
public:
    KeyReducerCmd();
    ~KeyReducerCmd(){}
    
    MStatus doIt(const MArgList&);
    bool isUndoable() const;
    MStatus undoIt();
    MStatus redoIt();
    
    static MSyntax syntaxCreator();
    
    static void* creator();
    
private:
    
    MStatus keyReduce(MFnAnimCurve &curve);
    bool isAfterStartTime(const MTime &time);
    bool isBeforeEndTime(const MTime &time);
    void sampleCurve(MFnAnimCurve &curve);
    MStatus alignKeyTimes(const std::vector<MObject> &curves);
    struct CurveLockSnapshot
    {
        MObject curve;
        KeyReducerDetail::CurveLocks locks;
    };
    MStatus restoreCurveLocks(const std::vector<CurveLockSnapshot> &snapshots);
    std::vector<CurveLockSnapshot> locksBefore, locksAfter;
    
    MAnimCurveChange animCurveChange;
    int startTime, endTime;
    bool hasStartTime, hasEndTime;
    double deviation;
    bool preBake;
};

#endif
