package com.rokid.cxrswithcxrl

import android.app.Application

/**
 * 全局应用类 — 管理 CXR-L 连接生命周期
 */
class CXRLApp : Application() {

    companion object {
        lateinit var instance: CXRLApp
    }

    /** CXR-L 连接实例（复用） */
    var sharedLink: com.rokid.cxr.link.CXRLink? = null
        set(value) { field = value; checkSessionReady() }

    /** CXR-L + 蓝牙 是否都已连接 */
    var isSessionReady: Boolean = false
        private set

    /** 连接状态变化回调 */
    var onSessionReadyChanged: ((Boolean) -> Unit)? = null

    private fun checkSessionReady() {
        val ready = sharedLink != null
        if (ready != isSessionReady) {
            isSessionReady = ready
            onSessionReadyChanged?.invoke(ready)
        }
    }

    fun resetSession() {
        sharedLink = null
        isSessionReady = false
    }

    override fun onCreate() {
        super.onCreate()
        instance = this
    }
}
