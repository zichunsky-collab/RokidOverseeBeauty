package com.rokid.cxrswithcxrl.utils

import android.util.Log
import com.google.gson.Gson
import com.rokid.cxr.link.CXRLink
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.IOException
import java.util.concurrent.TimeUnit

/**
 * 后端 API 客户端 — 负责所有 HTTP 请求
 *
 * 接口：
 *   GET  /api/nearby?lat=&lng=         → 附近景点
 *   GET  /api/narration?spot_id=&sub_spot_id=&level=  → 讲解词
 *   POST /api/qa                       → 语音问答
 */
object ApiClient {

    private const val TAG = "ApiClient"

    // ⚠️ 部署后改成你的服务器地址
    var baseUrl = "http://10.0.2.2:5000"  // 模拟器访问宿主机
        set(value) { field = value.trimEnd('/') }

    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .writeTimeout(10, TimeUnit.SECONDS)
        .build()

    private val gson = Gson()

    // ─── 数据类 ────────────────────────────────────

    data class NearbyResult(
        val matched: Boolean = false,
        val in_scenic_area: Boolean = false,
        val scenic_spot: ScenicSpotInfo? = null,
        val sub_spot: SubSpotInfo? = null,
        val nearby_pois: List<Poi>? = null,
        val message: String? = null
    )
    data class ScenicSpotInfo(val id: String, val name: String, val distance: Int = 0)
    data class SubSpotInfo(val id: String, val name: String, val distance: Int = 0)
    data class Poi(val name: String, val address: String = "", val distance: String = "")

    data class NarrationResult(
        val spot_name: String = "",
        val level: String = "",
        val narration: String = "",
        val sub_spot_name: String = ""
    )

    data class QaRequest(
        val spot_id: String,
        val sub_spot_id: String,
        val question: String,
        val language: String = "zh"
    )
    data class QaResult(
        val answer: String = "",
        val source: String = "",
        val spot_name: String = ""
    )

    // ─── 回调接口 ──────────────────────────────────

    interface ApiCallback<T> {
        fun onSuccess(result: T)
        fun onError(error: String)
    }

    // ─── API 调用 ──────────────────────────────────

    /**
     * 查询附近景点
     */
    fun getNearby(lat: Double, lng: Double, callback: ApiCallback<NearbyResult>) {
        val url = "$baseUrl/api/nearby?lat=$lat&lng=$lng"
        val request = Request.Builder().url(url).get().build()

        Log.d(TAG, "GET $url")
        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                callback.onError("网络请求失败: ${e.message}")
            }
            override fun onResponse(call: Call, response: Response) {
                val body = response.body?.string() ?: return
                try {
                    val result = gson.fromJson(body, NearbyResult::class.java)
                    callback.onSuccess(result)
                } catch (e: Exception) {
                    callback.onError("解析失败: ${e.message}")
                }
            }
        })
    }

    /**
     * 获取讲解词
     */
    fun getNarration(
        spotId: String,
        subSpotId: String,
        level: String = "standard",
        callback: ApiCallback<NarrationResult>
    ) {
        val url = "$baseUrl/api/narration?spot_id=$spotId&sub_spot_id=$subSpotId&level=$level"
        val request = Request.Builder().url(url).get().build()

        Log.d(TAG, "GET $url")
        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                callback.onError("获取讲解词失败: ${e.message}")
            }
            override fun onResponse(call: Call, response: Response) {
                val body = response.body?.string() ?: return
                try {
                    val result = gson.fromJson(body, NarrationResult::class.java)
                    callback.onSuccess(result)
                } catch (e: Exception) {
                    callback.onError("解析失败: ${e.message}")
                }
            }
        })
    }

    /**
     * 语音问答
     */
    fun askQuestion(
        spotId: String,
        subSpotId: String,
        question: String,
        callback: ApiCallback<QaResult>
    ) {
        val request = QaRequest(spotId, subSpotId, question)
        val json = gson.toJson(request)
        val body = json.toRequestBody("application/json".toMediaType())

        val req = Request.Builder()
            .url("$baseUrl/api/qa")
            .post(body)
            .build()

        Log.d(TAG, "POST /api/qa body=$json")
        client.newCall(req).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                callback.onError("问答请求失败: ${e.message}")
            }
            override fun onResponse(call: Call, response: Response) {
                val respBody = response.body?.string() ?: return
                try {
                    val result = gson.fromJson(respBody, QaResult::class.java)
                    callback.onSuccess(result)
                } catch (e: Exception) {
                    callback.onError("解析失败: ${e.message}")
                }
            }
        })
    }
}
