//
//  LogicProMCPBridgeHostExtensionParameterAddresses.h
//  LogicProMCPBridgeHostExtension
//
//  Created by Shlomy Sasson on 27/06/2026.
//

#pragma once

#include <AudioToolbox/AUParameters.h>

typedef NS_ENUM(AUParameterAddress, LogicProMCPBridgeHostExtensionParameterAddress) {
    sendNote = 0,
    midiNoteNumber = 1
};
