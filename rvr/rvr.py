from ctypes import *

import sys, os

os.add_dll_directory(os.path.split(__file__)[0])
rvrDLL = WinDLL(os.path.join(os.path.split(__file__)[0], "rvr.dll"))

def RVRFUNC(name, restype, argtypes):
    func = getattr(rvrDLL, name)
    func.restype = restype
    func.argtypes = argtypes
    globals()[name] = func

RVRControllerLeft, RVRControllerRight = 0, 1
RVREyeLeft, RVREyeRight = 0, 1

class FramebufferDesc(Structure):
    _fields_ = [
        ("depthBuffer", c_uint32),
        ("renderTexture", c_uint32),
        ("renderFramebuffer", c_uint32),
        ("resolveTexture", c_uint32),
        ("resolveFramebuffer", c_uint32)
    ]

# leftEyeDesc, rightEyeDesc = \
#     FramebufferDesc.in_dll(rvrDLL, "leftEyeDesc"), FramebufferDesc.in_dll(rvrDLL, "rightEyeDesc")

RVRFUNC("RVRSetActionManifestPath", None, (c_char_p, ))
globals()["RVRSetActionManifestPath"](os.path.join(os.path.split(__file__)[0], "rvr_actions.json").encode())

RVRFUNC("RVRInit", c_bool, ())
RVRFUNC("RVRGetRecommendedRenderTargetSize", None, (POINTER(c_uint32), POINTER(c_uint32)))
RVRFUNC("RVRIsReady", c_bool, ())
RVRFUNC("RVRCreateFrameBuffer", c_bool, (c_int, c_int, POINTER(FramebufferDesc)))
RVRFUNC("RVRSetupStereoRenderTargets", c_bool, ())
RVRFUNC("RVRInitControllers", c_bool, ())
RVRFUNC("RVRInitEyes", c_bool, (c_float, c_float))
RVRFUNC("RVRUpdateHMDPoseMatrix", None, ())
RVRFUNC("RVRPollEvents", None, ())
RVRFUNC("RVRBeginRendering", c_bool, (c_int, ))
RVRFUNC("RVREndRendering", c_bool, ())
RVRFUNC("RVRRenderControllers", c_bool, ())
RVRFUNC("RVRSubmitFramebufferDescriptorsToCompositor", c_bool, ())
RVRFUNC("RVRShutdown", c_bool, ())
RVRFUNC("RVRDeleteFramebufferDescriptors", c_bool, ())
RVRFUNC("RVRGetControllerTriggerClickState", c_bool, (c_int, ))
RVRFUNC("RVRGetControllerTriggerClickRisingEdge", c_bool, (c_int, ))
RVRFUNC("RVRGetControllerTriggerClickFallingEdge", c_bool, (c_int, ))
RVRFUNC("RVRGetControllerGripClickState", c_bool, (c_int, ))
RVRFUNC("RVRGetControllerGripClickRisingEdge", c_bool, (c_int, ))
RVRFUNC("RVRGetControllerGripClickFallingEdge", c_bool, (c_int, ))
RVRFUNC("RVRGetControllerJoystickClickState", c_bool, (c_int, ))
RVRFUNC("RVRGetControllerJoystickClickRisingEdge", c_bool, (c_int, ))
RVRFUNC("RVRGetControllerJoystickClickFallingEdge", c_bool, (c_int, ))
RVRFUNC("RVRGetControllerTriggerTouchState", c_bool, (c_int, ))
RVRFUNC("RVRGetControllerTriggerTouchRisingEdge", c_bool, (c_int, ))
RVRFUNC("RVRGetControllerTriggerTouchFallingEdge", c_bool, (c_int, ))
RVRFUNC("RVRGetControllerGripTouchState", c_bool, (c_int, ))
RVRFUNC("RVRGetControllerGripTouchRisingEdge", c_bool, (c_int, ))
RVRFUNC("RVRGetControllerGripTouchFallingEdge", c_bool, (c_int, ))
RVRFUNC("RVRGetControllerJoystickTouchState", c_bool, (c_int, ))
RVRFUNC("RVRGetControllerJoystickTouchRisingEdge", c_bool, (c_int, ))
RVRFUNC("RVRGetControllerJoystickTouchFallingEdge", c_bool, (c_int, ))

RVRFUNC("RVRGetControllerButtonOneClickState", c_bool, (c_int, ))
RVRFUNC("RVRGetControllerButtonOneClickRisingEdge", c_bool, (c_int, ))
RVRFUNC("RVRGetControllerButtonOneClickFallingEdge", c_bool, (c_int, ))
RVRFUNC("RVRGetControllerButtonOneTouchState", c_bool, (c_int, ))
RVRFUNC("RVRGetControllerButtonOneTouchRisingEdge", c_bool, (c_int, ))
RVRFUNC("RVRGetControllerButtonOneTouchFallingEdge", c_bool, (c_int, ))
RVRFUNC("RVRGetControllerButtonTwoClickState", c_bool, (c_int, ))
RVRFUNC("RVRGetControllerButtonTwoClickRisingEdge", c_bool, (c_int, ))
RVRFUNC("RVRGetControllerButtonTwoClickFallingEdge", c_bool, (c_int, ))
RVRFUNC("RVRGetControllerButtonTwoTouchState", c_bool, (c_int, ))
RVRFUNC("RVRGetControllerButtonTwoTouchRisingEdge", c_bool, (c_int, ))
RVRFUNC("RVRGetControllerButtonTwoTouchFallingEdge", c_bool, (c_int, ))

class vec2(Structure):
    _fields_ = [
        ("x", c_float),
        ("y", c_float)
    ]

    def get(self):
        return (c_float * 3)(self.x, self.y)

class vec3(Structure):
    _fields_ = [
        ("x", c_float),
        ("y", c_float),
        ("z", c_float)
    ]

    def get(self):
        return (c_float * 3)(self.x, self.y, self.z)

class vec4(Structure):
    _fields_ = [
        ("x", c_float),
        ("y", c_float),
        ("z", c_float),
        ("w", c_float)
    ]

    def get(self):
        return (c_float * 3)(self.x, self.y, self.z, self.w)

class mat4(Structure):
    _fields_ = [
        ("value", (c_float * 16))
    ]

RVRFUNC("RVRGetEyeResolveTexture", c_uint32, (c_int, ))

RVRFUNC("RVRSetControllerShowState", None, (c_int, c_bool))
RVRFUNC("RVRGetControllerShowState", c_bool, (c_int, ))

RVRFUNC("RVRGetControllerPoseMatrixArray", POINTER(c_float), (c_int, ))
RVRFUNC("RVRGetControllerPoseMatrix", mat4, (c_int, ))
RVRFUNC("RVRGetControllerPosition", vec3, (c_int, ))
RVRFUNC("RVRGetHmdPoseMatrixArray", POINTER(c_float), ())
RVRFUNC("RVRGetHmdPoseMatrix", mat4, ())
RVRFUNC("RVRGetHmdPosition", vec3, ())

RVRFUNC("RVRGetControllerTriggerPull", c_float, (c_int, ))
RVRFUNC("RVRGetControllerGripPull", c_float, (c_int, ))
RVRFUNC("RVRGetControllerJoystickPosition", vec2, (c_int, ))
RVRFUNC("RVRTriggerHapticVibration", None, (c_int, c_float, c_float, c_float))

RVRFUNC("RVRGetProjectionMatrixArray", POINTER(c_float), (c_int, c_float, c_float))
RVRFUNC("RVRGetProjectionMatrix", mat4, (c_int, c_float, c_float))
RVRFUNC("RVRGetEyePoseMatrixArray", POINTER(c_float), (c_int, ))
RVRFUNC("RVRGetEyePoseMatrix", mat4, (c_int, ))
RVRFUNC("RVRGetCurrentViewProjectionMatrixArray", POINTER(c_float), (c_int, ))
RVRFUNC("RVRGetCurrentViewProjectionMatrix", mat4, (c_int, ))
RVRFUNC("RVRGetCurrentViewProjectionNoPoseMatrixArray", POINTER(c_float), (c_int, ))
RVRFUNC("RVRGetCurrentViewProjectionNoPoseMatrix", mat4, (c_int, ))
RVRFUNC("RVRGetHmdDirection", vec3, ())