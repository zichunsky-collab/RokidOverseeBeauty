package com.rokid.cxrswithcxrl.utils

import android.util.Log
import com.google.gson.Gson

/**
 * 眼镜连接管理 + 自定义View推送
 *
 * 核心职责：
 *   1. 初始化 CXRLink 连接
 *   2. 推送讲解词到眼镜 AR 屏幕
 *   3. 更新/关闭眼镜显示
 *   4. 拍照（视觉识别）
 */
object GlassManager {

    private const val TAG = "GlassManager"

    private var cxrLink: com.rokid.cxr.link.CXRLink? = null
    private var isConnected = false

    private val gson = Gson()

    // ─── 连接 ─────────────────────────────────────

    /**
     * 初始化 CXR-L 连接
     * @param appCtx Application context
     */
    fun init(appCtx: android.app.Application) {
        if (cxrLink != null) return
        cxrLink = com.rokid.cxr.link.CXRLink(appCtx)

        cxrLink?.setCXRLinkCbk(object : com.rokid.cxr.link.callbacks.ICXRLinkCbk {
            override fun onCXRLConnected(connected: Boolean) {
                Log.i(TAG, "onCXRLConnected: $connected")
                isConnected = connected
                (appCtx as? com.rokid.cxrswithcxrl.CXRLApp)?.let {
                    it.sharedLink = if (connected) cxrLink else null
                }
            }

            override fun onGlassBtConnected(connected: Boolean) {
                Log.i(TAG, "onGlassBtConnected: $connected")
                if (!connected) {
                    isConnected = false
                    (appCtx as? com.rokid.cxrswithcxrl.CXRLApp)?.sharedLink = null
                }
            }

            override fun onGlassAiAssistStart() {}
            override fun onGlassAiAssistStop() {}
            override fun onGlassAiInterrupt(interruptWake: Boolean) {}
            override fun onGlassDeviceInfo(deviceInfo: com.rokid.cxr.link.utils.GlassInfo?) {}
            override fun onGlassWearingStatus(wearing: Boolean) {}
        })

        Log.i(TAG, "CXRLink initialized")
    }

    // ─── 自定义View推送 ──────────────────────────────

    /**
     * 在眼镜上显示讲解词
     * @param title 标题（景点名）
     * @param content 讲解内容
     */
    fun showNarration(title: String, content: String) {
        if (!isConnected || cxrLink == null) {
            Log.w(TAG, "showNarration: not connected")
            return
        }
        val json = buildNarrationView(title, content)
        cxrLink?.customViewOpen(json)
        Log.d(TAG, "customViewOpen: title=$title")
    }

    /**
     * 更新眼镜上的讲解内容
     */
    fun updateNarration(title: String, content: String) {
        if (!isConnected || cxrLink == null) return
        val json = buildNarrationView(title, content)
        cxrLink?.customViewUpdate(json)
        Log.d(TAG, "customViewUpdate")
    }

    /**
     * 关闭眼镜上的显示
     */
    fun closeView() {
        if (!isConnected || cxrLink == null) return
        cxrLink?.customViewClose()
        Log.d(TAG, "customViewClose")
    }

    // ─── 拍照 ─────────────────────────────────────

    /**
     * 调用眼镜摄像头拍照
     * @param callback 返回 Bitmap 字节数组，null 表示失败
     */
    fun takePhoto(callback: (ByteArray?) -> Unit) {
        if (!isConnected || cxrLink == null) {
            Log.w(TAG, "takePhoto: not connected")
            callback(null)
            return
        }
        cxrLink?.setCXRImageCbk(object : com.rokid.cxr.link.callbacks.IImageStreamCbk {
            override fun onImageReceived(data: ByteArray?) {
                cxrLink?.setCXRImageCbk(null)
                callback(data)
            }
            override fun onImageError(code: Int, msg: String?) {
                Log.e(TAG, "takePhoto error: code=$code msg=$msg")
                cxrLink?.setCXRImageCbk(null)
                callback(null)
            }
        })
        val success = cxrLink?.takePhoto(1024, 768, 80) ?: false
        if (!success) {
            cxrLink?.setCXRImageCbk(null)
            callback(null)
        }
    }

    // ─── 构建眼镜端UI JSON ──────────────────────────

    private fun buildNarrationView(title: String, content: String): String {
        val children = mutableListOf<Map<String, Any>>()

        // 景点名（标题）
        if (title.isNotEmpty()) {
            children.add(mapOf(
                "type" to "TextView",
                "props" to mapOf(
                    "id" to "title",
                    "text" to title,
                    "textSize" to "16sp",
                    "textStyle" to "bold",
                    "textColor" to "#FFFFFFFF",
                    "paddingBottom" to "10dp"
                )
            ))
        }

        // 分隔线
        children.add(mapOf(
            "type" to "View",
            "props" to mapOf(
                "id" to "divider",
                "layout_width" to "match_parent",
                "layout_height" to "1dp",
                "backgroundColor" to "#33FFFFFF"
            )
        ))

        // 讲解内容
        if (content.isNotEmpty()) {
            children.add(mapOf(
                "type" to "TextView",
                "props" to mapOf(
                    "id" to "content",
                    "text" to content,
                    "textSize" to "13sp",
                    "textColor" to "#FFCCCCCC",
                    "lineSpacingMultiplier" to "1.4",
                    "paddingTop" to "10dp"
                )
            ))
        }

        val layout = mapOf(
            "type" to "LinearLayout",
            "props" to mapOf(
                "id" to "main",
                "layout_width" to "match_parent",
                "layout_height" to "wrap_content",
                "orientation" to "vertical",
                "padding" to "20dp",
                "backgroundColor" to "#CC000000"
            ),
            "children" to children
        )

        return gson.toJson(layout)
    }
}
