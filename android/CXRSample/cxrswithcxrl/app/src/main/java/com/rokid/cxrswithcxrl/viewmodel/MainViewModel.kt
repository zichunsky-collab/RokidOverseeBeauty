package com.rokid.cxrswithcxrl.viewmodel

import android.app.Application
import android.util.Log
import androidx.lifecycle.AndroidViewModel
import com.rokid.cxrswithcxrl.utils.ApiClient
import com.rokid.cxrswithcxrl.utils.GlassManager
import com.rokid.cxrswithcxrl.utils.LocationTracker
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * 主 ViewModel — 串联：定位 → 后端 → 眼镜
 */
class MainViewModel(app: Application) : AndroidViewModel(app) {

    companion object {
        private const val TAG = "MainVM"
    }

    // ─── UI 状态 ──────────────────────────────────

    /** 眼镜连接状态 */
    private val _glassState = MutableStateFlow("眼镜：未连接")
    val glassState = _glassState.asStateFlow()

    /** GPS 状态 */
    private val _gpsState = MutableStateFlow("GPS：等待定位...")
    val gpsState = _gpsState.asStateFlow()

    /** 当前景点 */
    private val _spotName = MutableStateFlow("")
    val spotName = _spotName.asStateFlow()

    /** 讲解内容 */
    private val _narration = MutableStateFlow("讲解内容将在这里显示...")
    val narration = _narration.asStateFlow()

    /** 错误/提示信息 */
    private val _message = MutableStateFlow("")
    val message = _message.asStateFlow()

    /** 当前所在景点ID */
    private var currentSpotId: String? = null
    private var currentSubSpotId: String? = null

    // ─── 初始化 ──────────────────────────────────

    fun init() {
        val app = getApplication<Application>()

        // 1. 初始化眼镜连接
        GlassManager.init(app)

        // 2. 监听眼镜连接状态
        (app as? com.rokid.cxrswithcxrl.CXRLApp)?.onSessionReadyChanged = { ready ->
            _glassState.value = if (ready) "眼镜：已连接 ✓" else "眼镜：未连接"
            if (ready) {
                Log.i(TAG, "Glass connected, starting location tracker...")
                startLocationTracking()
            }
        }

        // 3. 如果已经连好，直接启动定位
        if ((app as? com.rokid.cxrswithcxrl.CXRLApp)?.isSessionReady == true) {
            _glassState.value = "眼镜：已连接 ✓"
            startLocationTracking()
        }
    }

    // ─── 定位 ──────────────────────────────────

    private fun startLocationTracking() {
        val app = getApplication<Application>()

        LocationTracker.start(app, 5000L, object : LocationTracker.LocationCallback {
            override fun onSpotFound(spotId: String, spotName: String, subSpotId: String, subSpotName: String, distance: Int) {
                Log.i(TAG, "Spot found: $spotName > $subSpotName (${distance}m)")
                _spotName.value = "$spotName · $subSpotName"
                _gpsState.value = "📍 距离 ${distance}m"
                currentSpotId = spotId
                currentSubSpotId = subSpotId

                // 获取讲解词
                fetchNarration(spotId, subSpotId)
            }

            override fun onNotInScenicArea(pois: List<ApiClient.Poi>) {
                _spotName.value = ""
                _narration.value = "讲解内容将在这里显示..."
                currentSpotId = null
                currentSubSpotId = null

                _gpsState.value = if (pois.isNotEmpty()) {
                    "不在景区内 | 附近：${pois.take(2).joinToString("、") { it.name }}"
                } else {
                    "GPS：不在景区范围内"
                }
                // 关闭眼镜上的显示
                GlassManager.closeView()
            }

            override fun onError(msg: String) {
                _gpsState.value = "⚠️ $msg"
            }

            override fun onLocationUpdate(lat: Double, lng: Double) {
                // 可以在 UI 上显示坐标，暂时不处理
            }
        })
    }

    // ─── 讲解词 ──────────────────────────────────

    private fun fetchNarration(spotId: String, subSpotId: String, level: String = "standard") {
        ApiClient.getNarration(spotId, subSpotId, level, object : ApiClient.ApiCallback<ApiClient.NarrationResult> {
            override fun onSuccess(result: ApiClient.NarrationResult) {
                val content = result.narration
                val title = result.spot_name.ifEmpty { result.sub_spot_name }
                _narration.value = content
                GlassManager.showNarration(title, content)
            }

            override fun onError(error: String) {
                _message.value = "获取讲解词失败: $error"
            }
        })
    }

    // ─── 讲解深度切换 ──────────────────────────────

    fun setLevel(level: String) {
        val spotId = currentSpotId ?: return
        val subSpotId = currentSubSpotId ?: return
        fetchNarration(spotId, subSpotId, level)
    }

    // ─── 问答 ──────────────────────────────────

    fun askQuestion(question: String) {
        val spotId = currentSpotId
        val subSpotId = currentSubSpotId
        if (spotId == null || subSpotId == null) {
            _message.value = "请先进入景区"
            return
        }

        ApiClient.askQuestion(spotId, subSpotId, question, object : ApiClient.ApiCallback<ApiClient.QaResult> {
            override fun onSuccess(result: ApiClient.QaResult) {
                _narration.value = result.answer
                GlassManager.showNarration("💬 问答", result.answer)
            }

            override fun onError(error: String) {
                _message.value = "问答失败: $error"
            }
        })
    }

    // ─── 拍照 ──────────────────────────────────

    fun takePhoto(callback: (ByteArray?) -> Unit) {
        GlassManager.takePhoto(callback)
    }

    // ─── 生命周期 ──────────────────────────────────

    fun onResume() {
        // 定位已经在 init 时启动
    }

    fun onPause() {
        // 保持定位运行（后台继续识别景点）
    }

    override fun onCleared() {
        super.onCleared()
        LocationTracker.stop()
        GlassManager.closeView()
    }
}
