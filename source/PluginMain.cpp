#include <maya/MFnPlugin.h>
#include <maya/MGlobal.h>

#include "keyReducerCmd.h"
#include "restoreKeys.h"


MStatus initializePlugin( MObject obj )
{
	MStatus status = MStatus::kSuccess;
	MFnPlugin plugin( obj, "tcKeyReducer", "1.0", "Any");
    MString errorString;
    
	status = plugin.registerCommand("tcKeyReducer", KeyReducerCmd::creator, KeyReducerCmd::syntaxCreator);
	if(!status)
	{
		MGlobal::displayError("Error registering tcKeyReducer");
		return status;
	}
    
    status = plugin.registerCommand("tcStoreKeys", StoreKeysCmd::creator, StoreKeysCmd::syntaxCreator);
	if(!status)
	{
		MGlobal::displayError("Error registering tcStoreKeys");
		return status;
	}
    
    status = plugin.registerCommand("tcRestoreKeys", RestoreKeysCmd::creator, RestoreKeysCmd::syntaxCreator);
	if(!status)
	{
		MGlobal::displayError("Error registering tcRestoreKeys");
		return status;
	}
    
	MString command;
	command = "print('Load KeyReducer')";
	MGlobal::executeCommand(command, true, false);

	return status;
}

MStatus uninitializePlugin( MObject obj)
{
	MStatus status = MStatus::kSuccess;
	MFnPlugin plugin( obj );
	status = plugin.deregisterCommand("tcKeyReducer");
    if (!status)
	{
		MGlobal::displayError("Error deregistering node tcKeyReducer");
		return status;
	}
    
    status = plugin.deregisterCommand("tcStoreKeys");
    if (!status)
	{
		MGlobal::displayError("Error deregistering node tcStoreKeys");
		return status;
	}
    
    status = plugin.deregisterCommand("tcRestoreKeys");
    if (!status)
	{
		MGlobal::displayError("Error deregistering node tcRestoreKeys");
		return status;
	}
        
	return status;
}
