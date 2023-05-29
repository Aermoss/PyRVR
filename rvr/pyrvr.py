import openvr as vr
import os, glm

from pyglet.gl import *
from ctypes import *

hmd, currentEye = None, None
driver, display = None, None
trackedDevicePose = (vr.TrackedDevicePose_t * vr.k_unMaxTrackedDeviceCount)()
devicePoseMatrix = [glm.mat4()] * vr.k_unMaxTrackedDeviceCount
deviceClassChar = [0] * vr.k_unMaxTrackedDeviceCount
poseClasses = None
validPoseCount = None
hmdPose = None

RVREyeLeft, RVREyeRight = 0, 1
RVRControllerLeft, RVRControllerRight = 0, 1

class RVRControllerInfo:
    source = vr.k_ulInvalidInputValueHandle
    actionPose = vr.k_ulInvalidActionHandle
    actionHaptic = vr.k_ulInvalidActionHandle
    actionJoystickClick = vr.k_ulInvalidActionHandle
    actionJoystickTouch = vr.k_ulInvalidActionHandle
    actionJoystickPosition = vr.k_ulInvalidActionHandle
    actionTriggerClick = vr.k_ulInvalidActionHandle
    actionTriggerTouch = vr.k_ulInvalidActionHandle
    actionTriggerPull = vr.k_ulInvalidActionHandle
    actionGripClick = vr.k_ulInvalidActionHandle
    actionGripTouch = vr.k_ulInvalidActionHandle
    actionGripPull = vr.k_ulInvalidActionHandle
    actionButtonOneClick = vr.k_ulInvalidActionHandle
    actionButtonOneTouch = vr.k_ulInvalidActionHandle
    actionButtonTwoClick = vr.k_ulInvalidActionHandle
    actionButtonTwoTouch = vr.k_ulInvalidActionHandle
    poseMatrix = None
    renderModel = None
    renderModelName = None
    showController = True

RVRControllers = [RVRControllerInfo(), RVRControllerInfo()]
renderModels = []
actionSetRVR = None

class FramebufferDesc:
    depthBuffer = c_uint32()
    renderTexture = c_uint32()
    renderFramebuffer = c_uint32()
    resolveTexture = c_uint32()
    resolveFramebuffer = c_uint32()

leftEyeDesc = FramebufferDesc()
rightEyeDesc = FramebufferDesc()

renderModelProgram, renderModelMatrixLocation = c_uint32(), c_uint32()

RVRTrackedDeviceDeactivateCallback = lambda: ...
RVRTrackedDeviceUpdateCallback = lambda: ...

class RVRCGLRenderModel:
    def __init__(self, modelName):
        self.modelName = modelName
        self.renderModel = None
        self.textureMap = None
        self.vao, self.vbo, self.ibo, self.tex = \
            c_uint32(), c_uint32(), c_uint32(), c_uint32()

    def __del__(self):
        self.destroy()

    def init(self, model, texture):
        self.renderModel = model
        self.textureMap = texture

        glGenVertexArrays(1, byref(self.vao))
        glBindVertexArray(self.vao)

        glGenBuffers(1, byref(self.vbo))
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, sizeof(c_float) * 8 * self.renderModel.unVertexCount, self.renderModel.rVertexData, GL_STATIC_DRAW)

        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, sizeof(c_float) * 8, sizeof(c_float) * 0)
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, sizeof(c_float) * 8, sizeof(c_float) * 3)
        glEnableVertexAttribArray(2)
        glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, sizeof(c_float) * 8, sizeof(c_float) * 6)

        glGenBuffers(1, byref(self.ibo))
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ibo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, sizeof(c_uint16) * self.renderModel.unTriangleCount * 3, self.renderModel.rIndexData, GL_STATIC_DRAW)

        glBindVertexArray(0)
        glGenTextures(1, byref(self.tex))
        glBindTexture(GL_TEXTURE_2D, self.tex)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.textureMap.unWidth, self.textureMap.unHeight, 0, GL_RGBA, GL_UNSIGNED_BYTE, self.textureMap.rubTextureMapData)

        glGenerateMipmap(GL_TEXTURE_2D)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glBindTexture(GL_TEXTURE_2D, 0)
        return True

    def render(self):
        if self.vbo:
            glBindVertexArray(self.vao)
            glActiveTexture(GL_TEXTURE0)
            glBindTexture(GL_TEXTURE_2D, self.tex)
            glDrawElements(GL_TRIANGLES, self.renderModel.unTriangleCount * 3, GL_UNSIGNED_SHORT, 0)
            glBindVertexArray(0)

        return True

    def destroy(self):
        vr.VRRenderModels().freeRenderModel(self.renderModel)
        vr.VRRenderModels().freeTexture(self.textureMap)

        if self.vbo:
            glDeleteBuffers(1, byref(self.ibo))
            glDeleteVertexArrays(1, byref(self.vao))
            glDeleteBuffers(1, byref(self.vbo))
            glDeleteTextures(1, byref(self.tex))

        return True

    def getName(self):
        return self.modelName

    def getRenderModel(self):
        return self.renderModel

    def getTextureMap(self):
        return self.textureMap

def RVRSetTrackedDeviceDeactivateCallback(func):
    global RVRTrackedDeviceDeactivateCallback
    RVRTrackedDeviceDeactivateCallback = func

def RVRSetTrackedDeviceUpdateCallback(func):
    global RVRTrackedDeviceUpdateCallback
    RVRTrackedDeviceUpdateCallback = func

def RVRConvertvrMatrixToGLMMatrix(mat):
    return glm.mat4(
        mat.m[0][0], mat.m[1][0], mat.m[2][0], 0.0,
        mat.m[0][1], mat.m[1][1], mat.m[2][1], 0.0,
        mat.m[0][2], mat.m[1][2], mat.m[2][2], 0.0,
        mat.m[0][3], mat.m[1][3], mat.m[2][3], 1.0
    )

def RVRGetTrackedDeviceString(unDevice, prop):
    return vr.VRSystem().getStringTrackedDeviceProperty(unDevice, prop)

def RVRGetRecommendedRenderTargetSize():
    return hmd.getRecommendedRenderTargetSize()

def RVRIsReady():
    if hmd: return True
    else: return False

def RVRCreateFrameBuffer(width, height, framebufferDesc):
    glGenFramebuffers(1, byref(framebufferDesc.renderFramebuffer))
    glBindFramebuffer(GL_FRAMEBUFFER, framebufferDesc.renderFramebuffer)
    glGenRenderbuffers(1, byref(framebufferDesc.depthBuffer))
    glBindRenderbuffer(GL_RENDERBUFFER, framebufferDesc.depthBuffer)
    glRenderbufferStorageMultisample(GL_RENDERBUFFER, 4, GL_DEPTH_COMPONENT, width, height)
    glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, framebufferDesc.depthBuffer)
    glGenTextures(1, byref(framebufferDesc.renderTexture))
    glBindTexture(GL_TEXTURE_2D_MULTISAMPLE, framebufferDesc.renderTexture)
    glTexImage2DMultisample(GL_TEXTURE_2D_MULTISAMPLE, 4, GL_RGBA8, width, height, True)
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D_MULTISAMPLE, framebufferDesc.renderTexture, 0)
    glGenFramebuffers(1, byref(framebufferDesc.resolveFramebuffer))
    glBindFramebuffer(GL_FRAMEBUFFER, framebufferDesc.resolveFramebuffer)
    glGenTextures(1, byref(framebufferDesc.resolveTexture))
    glBindTexture(GL_TEXTURE_2D, framebufferDesc.resolveTexture)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAX_LEVEL, 0)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, None)
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, framebufferDesc.resolveTexture, 0)
    status = glCheckFramebufferStatus(GL_FRAMEBUFFER)
    if status != GL_FRAMEBUFFER_COMPLETE: return False
    glBindFramebuffer(GL_FRAMEBUFFER, 0)
    return True

def RVRSetupStereoRenderTargets():
    if not RVRIsReady(): return False
    renderWidth, renderHeight = RVRGetRecommendedRenderTargetSize()
    RVRCreateFrameBuffer(renderWidth, renderHeight, leftEyeDesc)
    RVRCreateFrameBuffer(renderWidth, renderHeight, rightEyeDesc)
    return True

def RVRInitCompositor():
    if not vr.VRCompositor(): return False
    return True

def RVRCreateShaderProgram(vertexShaderSource, fragmentShaderSource):
    program = glCreateProgram()
    
    vertexShader = glCreateShader(GL_VERTEX_SHADER)
    src_buffer = create_string_buffer(vertexShaderSource.encode())
    buf_pointer = cast(pointer(pointer(src_buffer)), POINTER(POINTER(c_char)))
    length = c_int(len(vertexShaderSource) + 1)
    glShaderSource(vertexShader, 1, buf_pointer, byref(length))
    glCompileShader(vertexShader)
    isVertexShaderCompiled = c_int32()
    glGetShaderiv(vertexShader, GL_COMPILE_STATUS, byref(isVertexShaderCompiled))

    if isVertexShaderCompiled.value != GL_TRUE:
        length = c_int32()
        glGetShaderiv(vertexShader, GL_INFO_LOG_LENGTH, byref(length))
        buffer = create_string_buffer(length.value)
        glGetShaderInfoLog(vertexShader, length.value, None, buffer)
        print(buffer.value.decode())
        glDeleteProgram(program)
        glDeleteShader(vertexShader)
        return 0

    glAttachShader(program, vertexShader)
    glDeleteShader(vertexShader)

    fragmentShader = glCreateShader(GL_FRAGMENT_SHADER)
    src_buffer = create_string_buffer(fragmentShaderSource.encode())
    buf_pointer = cast(pointer(pointer(src_buffer)), POINTER(POINTER(c_char)))
    length = c_int(len(fragmentShaderSource) + 1)
    glShaderSource(fragmentShader, 1, buf_pointer, byref(length))
    glCompileShader(fragmentShader)
    isFragmentShaderCompiled = c_int32()
    glGetShaderiv(fragmentShader, GL_COMPILE_STATUS, byref(isFragmentShaderCompiled))

    if isFragmentShaderCompiled.value != GL_TRUE:
        length = c_int32()
        glGetShaderiv(fragmentShader, GL_INFO_LOG_LENGTH, byref(length))
        buffer = create_string_buffer(length.value)
        glGetShaderInfoLog(fragmentShader, length.value, None, buffer)
        print(buffer.value.decode())
        glDeleteProgram(program)
        glDeleteShader(fragmentShader)
        return 0

    glAttachShader(program, fragmentShader)
    glDeleteShader(fragmentShader)
    
    glLinkProgram(program)
    programSuccess = c_int32(GL_TRUE)
    glGetProgramiv(program, GL_LINK_STATUS, byref(programSuccess))

    if programSuccess.value != GL_TRUE:
        length = c_int32()
        glGetProgramiv(program, GL_INFO_LOG_LENGTH, byref(length))
        buffer = create_string_buffer(length.value)
        glGetProgramInfoLog(program, length.value, None, buffer)
        print(buffer.value.decode())
        glDeleteProgram(program)
        return 0

    return program

def RVRInitControllers():
    global renderModelProgram, renderModelMatrixLocation

    renderModelProgram = RVRCreateShaderProgram(
        "#version 460 core\n"
        "\n"
        "uniform mat4 matrix;\n"
        "layout(location = 0) in vec4 position;\n"
        "layout(location = 1) in vec3 normals;\n"
        "layout(location = 2) in vec2 texCoords;\n"
        "out vec2 fragTexCoords;\n"
        "\n"
        "void main() {\n"
        "   fragTexCoords = texCoords;\n"
        "   gl_Position = matrix * vec4(position.xyz, 1);\n"
        "}\n",
        "#version 460 core\n"
        "\n"
        "uniform sampler2D diffuse;\n"
        "in vec2 fragTexCoords;\n"
        "\n"
        "void main() {\n"
        "   gl_FragColor = texture(diffuse, fragTexCoords);\n"
        "}\n"
    )

    renderModelMatrixLocation = glGetUniformLocation(renderModelProgram, "matrix".encode())

    if renderModelMatrixLocation == -1:
        return False

    return renderModelProgram != 0

def RVRGetProjectionMatrix(eye, nearClip, farClip):
    if not RVRIsReady(): return glm.mat4(1.0)
    mat = hmd.getProjectionMatrix(eye, nearClip, farClip)

    return glm.mat4(
        mat.m[0][0], mat.m[1][0], mat.m[2][0], mat.m[3][0],
        mat.m[0][1], mat.m[1][1], mat.m[2][1], mat.m[3][1],
        mat.m[0][2], mat.m[1][2], mat.m[2][2], mat.m[3][2],
        mat.m[0][3], mat.m[1][3], mat.m[2][3], mat.m[3][3]
    )

def RVRGetEyePoseMatrix(eye):
    if not RVRIsReady(): return glm.mat4(1.0)
    mat = hmd.getEyeToHeadTransform(eye)

    return glm.inverse(glm.mat4(
        mat.m[0][0], mat.m[1][0], mat.m[2][0], 0.0,
        mat.m[0][1], mat.m[1][1], mat.m[2][1], 0.0,
        mat.m[0][2], mat.m[1][2], mat.m[2][2], 0.0,
        mat.m[0][3], mat.m[1][3], mat.m[2][3], 1.0
    ))

def RVRInitEyes(nearClip, farClip):
    global leftProjectionMatrix, rightProjectionMatrix
    global leftEyePosMatrix, rightEyePosMatrix
    leftProjectionMatrix = RVRGetProjectionMatrix(RVREyeLeft, nearClip, farClip)
    rightProjectionMatrix = RVRGetProjectionMatrix(RVREyeRight, nearClip, farClip)
    leftEyePosMatrix = RVRGetEyePoseMatrix(RVREyeLeft)
    rightEyePosMatrix = RVRGetEyePoseMatrix(RVREyeRight)
    return True

def RVRConvertOpenVRMatrixToGLMMatrix(mat):
    return glm.mat4(
        mat.m[0][0], mat.m[1][0], mat.m[2][0], 0.0,
        mat.m[0][1], mat.m[1][1], mat.m[2][1], 0.0,
        mat.m[0][2], mat.m[1][2], mat.m[2][2], 0.0,
        mat.m[0][3], mat.m[1][3], mat.m[2][3], 1.0
    )

def RVRShutdown():
    global hmd
    if not RVRIsReady(): return False
    vr.shutdown()
    hmd = None
    return True

def RVRIsInputAvailable():
    return hmd.isInputAvailable()

def RVRGetController(controller):
    return RVRControllers[controller]

def RVRSetControllerShowState(controller, state):
    RVRGetController(controller).showController = state

def RVRGetControllerShowState(controller):
    return RVRGetController(controller).showController

def RVRGetCurrentViewProjectionMatrix(eye):
    if eye == RVREyeLeft:
        return leftProjectionMatrix * leftEyePosMatrix * hmdPose

    if eye == RVREyeRight:
        return rightProjectionMatrix * rightEyePosMatrix * hmdPose

def RVRFindOrLoadModel(renderModelName):
    renderModel = None

    for i in renderModels:
        if i.getName() == renderModelName:
            renderModel = i

    if not renderModel:
        model = vr.VRRenderModels().loadRenderModel_Async(renderModelName)

        if not model:
            vr.VRRenderModels().freeRenderModel(model)
            return None

        texture = vr.VRRenderModels().loadTexture_Async(model.diffuseTextureId)

        if not texture:
            vr.VRRenderModels().freeTexture(texture)
            return None

        renderModel = RVRCGLRenderModel(renderModelName)

        if not renderModel.init(model, texture):
            renderModel = None

        else:
            renderModels.push_back(renderModel)

    return renderModel

def RVRGetEyeDesc(eye):
    if eye == RVREyeLeft: return leftEyeDesc
    if eye == RVREyeRight: return rightEyeDesc

def RVRGetCurrentEye():
    return currentEye

def RVRSetCurrentEye(eye):
    global currentEye
    currentEye = eye

def RVRBeginRendering(eye):
    glEnable(GL_MULTISAMPLE)
    glBindFramebuffer(GL_FRAMEBUFFER, leftEyeDesc.renderFramebuffer if eye == RVREyeLeft else rightEyeDesc.renderFramebuffer)
    renderWidth, renderHeight = RVRGetRecommendedRenderTargetSize()
    glViewport(0, 0, renderWidth, renderHeight)
    RVRSetCurrentEye(eye)
    return True

def RVREndRendering():
    glBindFramebuffer(GL_FRAMEBUFFER, 0)
    glDisable(GL_MULTISAMPLE)
    glBindFramebuffer(GL_READ_FRAMEBUFFER, RVRGetEyeDesc(RVRGetCurrentEye()).renderFramebuffer)
    glBindFramebuffer(GL_DRAW_FRAMEBUFFER, RVRGetEyeDesc(RVRGetCurrentEye()).resolveFramebuffer)
    renderWidth, renderHeight = RVRGetRecommendedRenderTargetSize()
    glBlitFramebuffer(0, 0, renderWidth, renderHeight, 0, 0, renderWidth, renderHeight, GL_COLOR_BUFFER_BIT, GL_LINEAR)
    glBindFramebuffer(GL_READ_FRAMEBUFFER, 0)
    glBindFramebuffer(GL_DRAW_FRAMEBUFFER, 0)
    RVRSetCurrentEye(RVREyeLeft)
    return True

def RVRSubmitFramebufferDescriptorsToCompositor():
    leftEyeTexture = vr.Texture_t()
    leftEyeTexture.handle = int(RVRGetEyeDesc(RVREyeLeft).resolveTexture.value)
    leftEyeTexture.eType = vr.TextureType_OpenGL
    leftEyeTexture.eColorSpace = vr.ColorSpace_Gamma

    rightEyeTexture = vr.Texture_t()
    rightEyeTexture.handle = int(RVRGetEyeDesc(RVREyeRight).resolveTexture.value)
    rightEyeTexture.eType = vr.TextureType_OpenGL
    rightEyeTexture.eColorSpace = vr.ColorSpace_Gamma

    try:
        vr.VRCompositor().submit(vr.Eye_Left, leftEyeTexture)
        vr.VRCompositor().submit(vr.Eye_Right, rightEyeTexture)

    except vr.error_code.CompositorError_DoNotHaveFocus:
        return False

    return True

def RVRDeleteFramebufferDescriptors():
    glDeleteRenderbuffers(1, byref(leftEyeDesc.depthBuffer))
    glDeleteTextures(1, byref(leftEyeDesc.renderTexture))
    glDeleteFramebuffers(1, byref(leftEyeDesc.renderFramebuffer))
    glDeleteTextures(1, byref(leftEyeDesc.resolveTexture))
    glDeleteFramebuffers(1, byref(leftEyeDesc.resolveFramebuffer))

    glDeleteRenderbuffers(1, byref(rightEyeDesc.depthBuffer))
    glDeleteTextures(1, byref(rightEyeDesc.renderTexture))
    glDeleteFramebuffers(1, byref(rightEyeDesc.renderFramebuffer))
    glDeleteTextures(1, byref(rightEyeDesc.resolveTexture))
    glDeleteFramebuffers(1, byref(rightEyeDesc.resolveFramebuffer))
    return True

def RVRCompositorWaitGetPoses(renderPoseArray, poseArray):
    return vr.VRCompositor().waitGetPoses(renderPoseArray, poseArray)

def RVRGetTrackedDeviceClass(number):
    return hmd.getTrackedDeviceClass(number)

def RVRGetControllerRoleForTrackedDeviceIndex(index):
    return vr.VRSystem().getControllerRoleForTrackedDeviceIndex(index)

def RVRUpdateHMDPoseMatrix():
    global hmdPose, trackedDevicePose, validPoseCount, deviceClassChar, poseClasses

    if not RVRIsReady(): return
    trackedDevicePose, _ = RVRCompositorWaitGetPoses(trackedDevicePose, None)

    validPoseCount = 0
    poseClasses = ""

    for deviceNumber in range(vr.k_unMaxTrackedDeviceCount):
        if trackedDevicePose[deviceNumber].bPoseIsValid:
            validPoseCount += 1
            devicePoseMatrix[deviceNumber] = RVRConvertOpenVRMatrixToGLMMatrix(trackedDevicePose[deviceNumber].mDeviceToAbsoluteTracking)

            if deviceClassChar[deviceNumber] == 0:
                match RVRGetTrackedDeviceClass(deviceNumber):
                    case vr.TrackedDeviceClass_Controller:
                        deviceClassChar[deviceNumber] = "C"
                        break

                    case vr.TrackedDeviceClass_HMD:
                        deviceClassChar[deviceNumber] = "H"
                        break

                    case vr.TrackedDeviceClass_Invalid:
                        deviceClassChar[deviceNumber] = "I"
                        break

                    case vr.TrackedDeviceClass_GenericTracker:
                        deviceClassChar[deviceNumber] = "G"
                        break

                    case vr.TrackedDeviceClass_TrackingReference:
                        deviceClassChar[deviceNumber] = "T"
                        break

                    case _:
                        deviceClassChar[deviceNumber] = "?"
                        break

            poseClasses += deviceClassChar[deviceNumber]
            
    if trackedDevicePose[vr.k_unTrackedDeviceIndex_Hmd].bPoseIsValid:
        hmdPose = glm.inverse(devicePoseMatrix[vr.k_unTrackedDeviceIndex_Hmd])

def RVRRenderControllers():
    glUseProgram(renderModelProgram)

    for controller in [RVRControllerLeft, RVRControllerRight]:
        if not RVRGetControllerShowState(controller) or not RVRGetController(controller).renderModel:
            continue

        matDeviceToTracking = RVRGetController(controller).poseMatrix
        matMVP = RVRGetCurrentViewProjectionMatrix(RVRGetCurrentEye()) * matDeviceToTracking
        glUniformMatrix4fv(renderModelMatrixLocation, 1, GL_FALSE, glm.value_ptr(matMVP))
        RVRGetController(controller).renderModel.render()

    glUseProgram(0)
    return True

def RVRGetDigitalActionRisingEdge(action):
    actionData = vr.VRInput().getDigitalActionData(action, vr.k_ulInvalidInputValueHandle)
    return actionData.bActive and actionData.bChanged and actionData.bState

def RVRGetDigitalActionFallingEdge(action):
    actionData = vr.VRInput().getDigitalActionData(action, vr.k_ulInvalidInputValueHandle)
    return actionData.bActive and actionData.bChanged and not actionData.bState

def RVRGetDigitalActionState(action):
    actionData = vr.VRInput().getDigitalActionData(action, vr.k_ulInvalidInputValueHandle)
    return actionData.bActive and actionData.bChanged

def RVRGetControllerTriggerClickState(controller):
    return RVRGetDigitalActionState(RVRGetController(controller).actionTriggerClick)

def RVRGetControllerTriggerClickRisingEdge(controller):
    return RVRGetDigitalActionRisingEdge(RVRGetController(controller).actionTriggerClick)

def RVRGetControllerTriggerClickFallingEdge(controller):
    return RVRGetDigitalActionFallingEdge(RVRGetController(controller).actionTriggerClick)

def RVRGetControllerGripClickState(controller):
    return RVRGetDigitalActionState(RVRGetController(controller).actionGripClick)

def RVRGetControllerGripClickRisingEdge(controller):
    return RVRGetDigitalActionRisingEdge(RVRGetController(controller).actionGripClick)

def RVRGetControllerGripClickFallingEdge(controller):
    return RVRGetDigitalActionFallingEdge(RVRGetController(controller).actionGripClick)

def RVRGetControllerJoystickClickState(controller):
    return RVRGetDigitalActionState(RVRGetController(controller).actionJoystickClick)

def RVRGetControllerJoystickClickRisingEdge(controller):
    return RVRGetDigitalActionRisingEdge(RVRGetController(controller).actionJoystickClick)

def RVRGetControllerJoystickClickFallingEdge(controller):
    return RVRGetDigitalActionFallingEdge(RVRGetController(controller).actionJoystickClick)

def RVRGetControllerTriggerTouchState(controller):
    return RVRGetDigitalActionState(RVRGetController(controller).actionTriggerTouch)

def RVRGetControllerTriggerTouchRisingEdge(controller):
    return RVRGetDigitalActionRisingEdge(RVRGetController(controller).actionTriggerTouch)

def RVRGetControllerTriggerTouchFallingEdge(controller):
    return RVRGetDigitalActionFallingEdge(RVRGetController(controller).actionTriggerTouch)

def RVRGetControllerGripTouchState(controller):
    return RVRGetDigitalActionState(RVRGetController(controller).actionGripTouch)

def RVRGetControllerGripTouchRisingEdge(controller):
    return RVRGetDigitalActionRisingEdge(RVRGetController(controller).actionGripTouch)

def RVRGetControllerGripTouchFallingEdge(controller):
    return RVRGetDigitalActionFallingEdge(RVRGetController(controller).actionGripTouch)

def RVRGetControllerJoystickTouchState(controller):
    return RVRGetDigitalActionState(RVRGetController(controller).actionJoystickTouch)

def RVRGetControllerJoystickTouchRisingEdge(controller):
    return RVRGetDigitalActionRisingEdge(RVRGetController(controller).actionJoystickTouch)

def RVRGetControllerJoystickTouchFallingEdge(controller):
    return RVRGetDigitalActionFallingEdge(RVRGetController(controller).actionJoystickTouch)

def RVRGetControllerButtonOneClickState(controller):
    return RVRGetDigitalActionState(RVRGetController(controller).actionButtonOneClick)

def RVRGetControllerButtonOneClickRisingEdge(controller):
    return RVRGetDigitalActionRisingEdge(RVRGetController(controller).actionButtonOneClick)

def RVRGetControllerButtonOneClickFallingEdge(controller):
    return RVRGetDigitalActionFallingEdge(RVRGetController(controller).actionButtonOneClick)

def RVRGetControllerButtonOneTouchState(controller):
    return RVRGetDigitalActionState(RVRGetController(controller).actionButtonOneTouch)

def RVRGetControllerButtonOneTouchRisingEdge(controller):
    return RVRGetDigitalActionRisingEdge(RVRGetController(controller).actionButtonOneTouch)

def RVRGetControllerButtonOneTouchFallingEdge(controller):
    return RVRGetDigitalActionFallingEdge(RVRGetController(controller).actionButtonOneTouch)

def RVRGetControllerButtonTwoClickState(controller):
    return RVRGetDigitalActionState(RVRGetController(controller).actionButtonTwoClick)

def RVRGetControllerButtonTwoClickRisingEdge(controller):
    return RVRGetDigitalActionRisingEdge(RVRGetController(controller).actionButtonTwoClick)

def RVRGetControllerButtonTwoClickFallingEdge(controller):
    return RVRGetDigitalActionFallingEdge(RVRGetController(controller).actionButtonTwoClick)

def RVRGetControllerButtonTwoTouchState(controller):
    return RVRGetDigitalActionState(RVRGetController(controller).actionButtonTwoTouch)

def RVRGetControllerButtonTwoTouchRisingEdge(controller):
    return RVRGetDigitalActionRisingEdge(RVRGetController(controller).actionButtonTwoTouch)

def RVRGetControllerButtonTwoTouchFallingEdge(controller):
    return RVRGetDigitalActionFallingEdge(RVRGetController(controller).actionButtonTwoTouch)

def RVRGetAnalogActionData(action):
    analogData = vr.VRInput().getAnalogActionData(action, vr.k_ulInvalidInputValueHandle)
    if analogData.bActive: return glm.vec2(analogData.x, analogData.y)
    return glm.vec2(0.0, 0.0)

def RVRGetControllerTriggerPull(controller):
    return RVRGetAnalogActionData(RVRGetController(controller).actionTriggerPull).x

def RVRGetControllerGripPull(controller):
    return RVRGetAnalogActionData(RVRGetController(controller).actionGripPull).x

def RVRGetControllerJoystickPosition(controller):
    return RVRGetAnalogActionData(RVRGetController(controller).actionJoystickPosition)

def RVRTriggerHapticVibration(controller, duration, frequency, amplitude):
    vr.VRInput().triggerHapticVibrationAction(RVRGetController(controller).actionHaptic, 0, duration, frequency, amplitude, vr.k_ulInvalidInputValueHandle)

def RVRCheckControllers():
    for controller in [RVRControllerLeft, RVRControllerRight]:
        poseData = vr.VRInput().getPoseActionDataForNextFrame(RVRGetController(controller).actionPose, vr.TrackingUniverseStanding, vr.k_ulInvalidInputValueHandle)

        if not poseData.bActive or not poseData.pose.bPoseIsValid:
            RVRSetControllerShowState(controller, False)

        else:
            RVRSetControllerShowState(controller, True)
            RVRGetController(controller).poseMatrix = RVRConvertOpenVRMatrixToGLMMatrix(poseData.pose.mDeviceToAbsoluteTracking)

            originInfo = vr.VRInput().getOriginTrackedDeviceInfo(poseData.activeOrigin)

            if originInfo.trackedDeviceIndex != vr.k_unTrackedDeviceIndexInvalid:
                sRenderModelName = RVRGetTrackedDeviceString(originInfo.trackedDeviceIndex, vr.Prop_RenderModelName_String)

                if sRenderModelName != RVRGetController(controller).renderModelName:
                    RVRGetController(controller).renderModel = RVRFindOrLoadModel(sRenderModelName)
                    RVRGetController(controller).renderModelName = sRenderModelName

def RVRPollEvents():
    event = vr.VREvent_t()

    while hmd.pollNextEvent(event):
        match event.eventType:
            case vr.VREvent_TrackedDeviceDeactivated:
                RVRTrackedDeviceDeactivateCallback(event.trackedDeviceIndex)
                break

            case vr.VREvent_TrackedDeviceUpdated:
                RVRTrackedDeviceUpdateCallback(event.trackedDeviceIndex)
                break

    actionSet = vr.VRActiveActionSet_t()
    actionSet.ulActionSet = actionSetRVR
    vr.VRInput().updateActionState(actionSet)
    RVRCheckControllers()

def RVRInit():
    global currentEye, hmd, driver, display, actionSetRVR

    RVRSetCurrentEye(RVREyeLeft)
    hmd = vr.init(vr.VRApplication_Scene)
    vr.VRCompositor()

    driver = "No Driver"
    display = "No Display"

    driver = RVRGetTrackedDeviceString(vr.k_unTrackedDeviceIndex_Hmd, vr.Prop_TrackingSystemName_String)
    display = RVRGetTrackedDeviceString(vr.k_unTrackedDeviceIndex_Hmd, vr.Prop_SerialNumber_String)

    os.add_dll_directory(os.path.split(__file__)[0].replace("\\", "/"))
    vr.VRInput().setActionManifestPath(os.path.split(__file__)[0].replace("\\", "/") + "/rvr_actions.json")
    actionSetRVR = vr.VRInput().getActionSetHandle("/actions/rvr")

    RVRControllers[0].actionHaptic = vr.VRInput().getActionHandle("/actions/rvr/out/haptic_left")
    RVRControllers[0].source = vr.VRInput().getInputSourceHandle("/user/hand/left")
    RVRControllers[0].actionPose = vr.VRInput().getActionHandle("/actions/rvr/in/hand_left")
    RVRControllers[0].actionJoystickClick = vr.VRInput().getActionHandle("/actions/rvr/in/left_joystick_click")
    RVRControllers[0].actionJoystickTouch = vr.VRInput().getActionHandle("/actions/rvr/in/left_joystick_touch") 
    RVRControllers[0].actionJoystickPosition = vr.VRInput().getActionHandle("/actions/rvr/in/left_joystick_position")
    RVRControllers[0].actionGripClick = vr.VRInput().getActionHandle("/actions/rvr/in/left_grip_click")
    RVRControllers[0].actionGripTouch = vr.VRInput().getActionHandle("/actions/rvr/in/left_grip_trouch")
    RVRControllers[0].actionGripPull = vr.VRInput().getActionHandle("/actions/rvr/in/left_grip_pull")
    RVRControllers[0].actionTriggerClick = vr.VRInput().getActionHandle("/actions/rvr/in/left_trigger_click")
    RVRControllers[0].actionTriggerTouch = vr.VRInput().getActionHandle("/actions/rvr/in/left_trigger_trouch")
    RVRControllers[0].actionTriggerPull = vr.VRInput().getActionHandle("/actions/rvr/in/left_trigger_pull")
    RVRControllers[0].actionButtonOneClick = vr.VRInput().getActionHandle("/actions/rvr/in/x_click")
    RVRControllers[0].actionButtonOneTouch = vr.VRInput().getActionHandle("/actions/rvr/in/x_trouch")
    RVRControllers[0].actionButtonTwoClick = vr.VRInput().getActionHandle("/actions/rvr/in/y_click")
    RVRControllers[0].actionButtonTwoTouch = vr.VRInput().getActionHandle("/actions/rvr/in/y_trouch")

    RVRControllers[1].actionHaptic = vr.VRInput().getActionHandle("/actions/rvr/out/haptic_right")
    RVRControllers[1].source = vr.VRInput().getInputSourceHandle("/user/hand/right")
    RVRControllers[1].actionPose = vr.VRInput().getActionHandle("/actions/rvr/in/hand_right")
    RVRControllers[1].actionJoystickClick = vr.VRInput().getActionHandle("/actions/rvr/in/right_joystick_click")
    RVRControllers[1].actionJoystickTouch = vr.VRInput().getActionHandle("/actions/rvr/in/right_joystick_touch")
    RVRControllers[1].actionJoystickPosition = vr.VRInput().getActionHandle("/actions/rvr/in/right_joystick_position")
    RVRControllers[1].actionGripClick = vr.VRInput().getActionHandle("/actions/rvr/in/right_grip_click")
    RVRControllers[1].actionGripTouch = vr.VRInput().getActionHandle("/actions/rvr/in/right_grip_trouch")
    RVRControllers[1].actionGripPull = vr.VRInput().getActionHandle("/actions/rvr/in/right_grip_pull")
    RVRControllers[1].actionTriggerClick = vr.VRInput().getActionHandle("/actions/rvr/in/right_trigger_click")
    RVRControllers[1].actionTriggerTouch = vr.VRInput().getActionHandle("/actions/rvr/in/right_trigger_trouch")
    RVRControllers[1].actionTriggerPull = vr.VRInput().getActionHandle("/actions/rvr/in/right_trigger_pull")
    RVRControllers[1].actionButtonOneClick = vr.VRInput().getActionHandle("/actions/rvr/in/a_click")
    RVRControllers[1].actionButtonOneTouch = vr.VRInput().getActionHandle("/actions/rvr/in/a_trouch")
    RVRControllers[1].actionButtonTwoClick = vr.VRInput().getActionHandle("/actions/rvr/in/b_click")
    RVRControllers[1].actionButtonTwoTouch = vr.VRInput().getActionHandle("/actions/rvr/in/b_trouch")
    return True