package com.rokid.cxrswithcxrl.utils

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import androidx.core.content.ContextCompat

/**
 * GPS 定位服务 — 定期查询位置，发现景点时触发讲解
 */
object LocationTracker {

    private const val TAG = "LocationTracker"
    private const val DEFAULT_INTERVAL_MS = 5000L  // 5秒

    private var locationManager: LocationManager? = null
    private var handler: Handler? = null
    private var isRunning = false
    private var intervalMs = DEFAULT_INTERVAL_MS

    private var lastLat: Double = 0.0
    private var lastLng: Double = 0.0
    private var currentSpotId: String? = null
    private var currentSubSpotId: String? = null

    // ─── 回调 ─────────────────────────────────────

    interface LocationCallback {
        /** 发现附近景点，应获取讲解词 */
        fun onSpotFound(spotId: String, spotName: String, subSpotId: String, subSpotName: String, distance: Int)
        /** 不在景区范围内 */
        fun onNotInScenicArea(nearbyPois: List<ApiClient.Poi>)
        /** 定位错误 */
        fun onError(msg: String)
        /** 位置更新（不触发讲解） */
        fun onLocationUpdate(lat: Double, lng: Double)
    }

    private var callback: LocationCallback? = null

    // ─── 启动/停止 ──────────────────────────────────

    fun start(ctx: Context, intervalMs: Long = DEFAULT_INTERVAL_MS, cb: LocationCallback) {
        if (isRunning) return
        this.callback = cb
        this.intervalMs = intervalMs
        this.handler = Handler(Looper.getMainLooper())
        this.locationManager = ctx.getSystemService(Context.LOCATION_SERVICE) as LocationManager

        // 检查权限
        if (ContextCompat.checkSelfPermission(ctx, Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            cb.onError("定位权限未授予")
            return
        }

        isRunning = true
        Log.i(TAG, "LocationTracker started, interval=${intervalMs}ms")

        // 立即查询一次
        handler?.post(queryRunnable)
    }

    fun stop() {
        isRunning = false
        handler?.removeCallbacksAndMessages(null)
        handler = null
        callback = null
        Log.i(TAG, "LocationTracker stopped")
    }

    /** 重置景点状态（离开景区后重新进入时调用） */
    fun resetSpot() {
        currentSpotId = null
        currentSubSpotId = null
    }

    // ─── 定位查询 + 后端请求 ────────────────────────

    private val queryRunnable = object : Runnable {
        override fun run() {
            if (!isRunning) return

            try {
                val location = locationManager?.getLastKnownLocation(LocationManager.GPS_PROVIDER)
                    ?: locationManager?.getLastKnownLocation(LocationManager.NETWORK_PROVIDER)

                if (location != null) {
                    lastLat = location.latitude
                    lastLng = location.longitude
                    callback?.onLocationUpdate(lastLat, lastLng)

                    // 调用后端查询附近景点
                    ApiClient.getNearby(lastLat, lastLng, object : ApiClient.ApiCallback<ApiClient.NearbyResult> {
                        override fun onSuccess(result: ApiClient.NearbyResult) {
                            if (result.matched && result.sub_spot != null && result.scenic_spot != null) {
                                val newSubSpotId = result.sub_spot.id
                                // 只有换了景点才重新获取讲解词
                                if (newSubSpotId != currentSubSpotId) {
                                    currentSpotId = result.scenic_spot.id
                                    currentSubSpotId = newSubSpotId
                                    callback?.onSpotFound(
                                        result.scenic_spot.id,
                                        result.scenic_spot.name,
                                        result.sub_spot.id,
                                        result.sub_spot.name,
                                        result.sub_spot.distance
                                    )
                                }
                            } else {
                                currentSpotId = null
                                currentSubSpotId = null
                                callback?.onNotInScenicArea(result.nearby_pois ?: emptyList())
                            }
                        }

                        override fun onError(error: String) {
                            callback?.onError(error)
                        }
                    })
                } else {
                    Log.d(TAG, "No location available yet")
                }
            } catch (e: SecurityException) {
                callback?.onError("定位权限被撤销")
                return
            }

            handler?.postDelayed(this, intervalMs)
        }
    }
}
