//
//  AudioUnitViewModel.swift
//  LogicProMCPBridgeHost
//
//  Created by Shlomy Sasson on 27/06/2026.
//

import SwiftUI
import AudioToolbox
import CoreAudioKit

struct AudioUnitViewModel {
    var showAudioControls: Bool = false
    var showMIDIContols: Bool = false
    var title: String = "-"
    var message: String = "No Audio Unit loaded.."
    var viewController: ViewController?
}
