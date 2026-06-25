# 镜览山河 - Android 端开发指南

## 架构概述

```
Android App (手机端)
├── GPS 定位 → 获取当前经纬度
├── HTTP 请求 → 调用后端 API（/api/nearby, /api/narration）
├── Rokid CXR-L SDK → 连接眼镜
│   ├── openCustomView() → 推送讲解词到眼镜 AR 屏幕
│   ├── updateCustomView() → 更新眼镜上的文字
│   ├── takeGlassPhoto() → 拍照（可选，用于视觉确认）
│   └── AudioStreamListener → 语音输入（可选，用于问答）
└── UI → 手机端控制面板
```

## 前置条件

1. **Rokid 开发者账号** + `.lc` 鉴权文件
2. **Android Studio** 最新版
3. **Rokid AI App** ≥ 1.7.14 已安装到手机
4. **眼镜已蓝牙配对**
5. **高德 API Key**（Web 服务类型）

## 第一步：创建 Android 项目

### 1.1 项目配置

在 `settings.gradle.kts` 中添加 Rokid Maven 仓库：

```kotlin
dependencyResolutionManagement {
    repositories {
        maven { url = uri("https://maven.rokid.com/repository/maven-public/") }
        maven { url = uri("https://maven.aliyun.com/repository/public/") }
        maven { url = uri("https://maven.aliyun.com/repository/google/") }
        google()
        mavenCentral()
    }
}
```

### 1.2 添加依赖

在 `app/build.gradle.kts` 中：

```kotlin
dependencies {
    // Rokid CXR-L SDK
    implementation("com.rokid.cxr:client-l:1.0.3")
    
    // 网络请求
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.google.code.gson:gson:2.10.1")
    
    // 定位
    implementation("com.amap.api:location:6.4.5")  // 高德定位SDK（可选）
    
    // UI
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("com.google.android.material:material:1.11.0")
}
```

### 1.3 鉴权文件

将 `.lc` 文件放到 `app/src/main/res/raw/` 目录。

## 第二步：连接 Rokid 眼镜

```kotlin
// GlassConnectionManager.kt
class GlassConnectionManager(private val context: Context) {
    
    private var cxrLink: CxrLink? = null
    private var isConnected = false
    
    // 连接眼镜
    fun connect(token: String, listener: ConnectionListener) {
        cxrLink = CxrLink(context)
        
        cxrLink?.setConnectionListener(object : CxrLinkConnectionListener {
            override fun onCXRLConnected(success: Boolean) {
                if (success) {
                    // CXR链路已连接
                    cxrLink?.connectBluetooth(token)
                }
                listener.onCxrLinkChanged(success)
            }
            
            override fun onGlassBtConnected(success: Boolean) {
                isConnected = success
                listener.onGlassConnected(success)
            }
        })
        
        cxrLink?.connect(token)
    }
    
    // 推送自定义View到眼镜
    fun showOnGlass(text: String, title: String = "") {
        if (!isConnected) return
        
        val viewJson = buildViewJson(text, title)
        cxrLink?.customViewOpen(viewJson)
    }
    
    // 更新眼镜上的文字
    fun updateOnGlass(text: String, title: String = "") {
        if (!isConnected) return
        
        val viewJson = buildViewJson(text, title)
        cxrLink?.customViewUpdate(viewJson)
    }
    
    // 关闭眼镜上的显示
    fun closeOnGlass() {
        cxrLink?.customViewClose()
    }
    
    // 构建眼镜端显示的JSON布局
    private fun buildViewJson(text: String, title: String): String {
        val children = mutableListOf<Map<String, Any>>()
        
        // 标题
        if (title.isNotEmpty()) {
            children.add(mapOf(
                "type" to "TextView",
                "props" to mapOf(
                    "id" to "title",
                    "text" to title,
                    "textSize" to "14sp",
                    "textStyle" to "bold",
                    "textColor" to "#FFFFFFFF",
                    "paddingBottom" to "8dp"
                )
            ))
        }
        
        // 讲解内容
        children.add(mapOf(
            "type" to "TextView",
            "props" to mapOf(
                "id" to "content",
                "text" to text,
                "textSize" to "12sp",
                "textColor" to "#FFCCCCCC",
                "lineSpacingMultiplier" to "1.3"
            )
        ))
        
        val layout = mapOf(
            "type" to "LinearLayout",
            "props" to mapOf(
                "id" to "main",
                "layout_width" to "match_parent",
                "layout_height" to "wrap_content",
                "orientation" to "vertical",
                "padding" to "16dp",
                "backgroundColor" to "#CC000000"  // 半透明黑色背景
            ),
            "children" to children
        )
        
        return Gson().toJson(layout)
    }
    
    interface ConnectionListener {
        fun onCxrLinkChanged(connected: Boolean)
        fun onGlassConnected(connected: Boolean)
    }
}
```

## 第三步：GPS 定位 + 后端 API 调用

```kotlin
// LocationService.kt
class LocationService(private val context: Context) {
    
    private var locationManager: LocationManager? = null
    private val handler = Handler(Looper.getMainLooper())
    private var isRunning = false
    
    // 后端API地址（部署后修改）
    private val baseUrl = "http://YOUR_SERVER:5000"
    private val client = OkHttpClient.Builder()
        .connectTimeout(5, java.util.concurrent.TimeUnit.SECONDS)
        .readTimeout(10, java.util.concurrent.TimeUnit.SECONDS)
        .build()
    
    // 开始定位轮询
    fun start(intervalMs: Long = 5000, callback: LocationCallback) {
        isRunning = true
        locationManager = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
        
        val runnable = object : Runnable {
            override fun run() {
                if (!isRunning) return
                try {
                    val location = locationManager?.getLastKnownLocation(LocationManager.GPS_PROVIDER)
                        ?: locationManager?.getLastKnownLocation(LocationManager.NETWORK_PROVIDER)
                    
                    location?.let {
                        queryNearby(it.latitude, it.longitude, callback)
                    }
                } catch (e: SecurityException) {
                    callback.onError("定位权限未授予")
                }
                handler.postDelayed(this, intervalMs)
            }
        }
        handler.post(runnable)
    }
    
    fun stop() {
        isRunning = false
        handler.removeCallbacksAndMessages(null)
    }
    
    // 查询附近景点
    private fun queryNearby(lat: Double, lng: Double, callback: LocationCallback) {
        val url = "$baseUrl/api/nearby?lat=$lat&lng=$lng"
        val request = Request.Builder().url(url).build()
        
        client.newCall(request).enqueue(object : okhttp3.Callback {
            override fun onFailure(call: okhttp3.Call, e: java.io.IOException) {
                callback.onError("网络请求失败: ${e.message}")
            }
            
            override fun onResponse(call: okhttp3.Call, response: okhttp3.Response) {
                val body = response.body?.string() ?: return
                val result = Gson().fromJson(body, NearbyResult::class.java)
                
                if (result.matched && result.sub_spot != null) {
                    callback.onSpotFound(result.scenic_spot!!, result.sub_spot!!)
                } else {
                    callback.onNotInScenicArea(result.nearby_pois ?: emptyList())
                }
            }
        })
    }
    
    // 获取讲解词
    fun getNarration(spotId: String, subSpotId: String, level: Int = 2, callback: NarrationCallback) {
        val url = "$baseUrl/api/narration?spot_id=$spotId&sub_spot_id=$subSpotId&level=$level"
        val request = Request.Builder().url(url).build()
        
        client.newCall(request).enqueue(object : okhttp3.Callback {
            override fun onFailure(call: okhttp3.Call, e: java.io.IOException) {
                callback.onError("获取讲解词失败: ${e.message}")
            }
            
            override fun onResponse(call: okhttp3.Call, response: okhttp3.Response) {
                val body = response.body?.string() ?: return
                val result = Gson().fromJson(body, NarrationResult::class.java)
                callback.onNarration(result)
            }
        })
    }
    
    // 问答
    fun askQuestion(spotId: String, subSpotId: String, question: String, callback: QACallback) {
        val json = Gson().toJson(mapOf(
            "spot_id" to spotId,
            "sub_spot_id" to subSpotId,
            "question" to question
        ))
        val body = json.toRequestBody("application/json".toMediaType())
        val request = Request.Builder()
            .url("$baseUrl/api/qa")
            .post(body)
            .build()
        
        client.newCall(request).enqueue(object : okhttp3.Callback {
            override fun onFailure(call: okhttp3.Call, e: java.io.IOException) {
                callback.onError("问答失败: ${e.message}")
            }
            
            override fun onResponse(call: okhttp3.Call, response: okhttp3.Response) {
                val respBody = response.body?.string() ?: return
                val result = Gson().fromJson(respBody, QAResult::class.java)
                callback.onAnswer(result)
            }
        })
    }
    
    // 数据类
    data class NearbyResult(
        val matched: Boolean,
        val in_scenic_area: Boolean,
        val scenic_spot: ScenicSpotInfo?,
        val sub_spot: SubSpotInfo?,
        val nearby_pois: List<POI>?,
        val message: String?
    )
    
    data class ScenicSpotInfo(val id: String, val name: String, val distance: Int)
    data class SubSpotInfo(val id: String, val name: String, val distance: Int)
    data class POI(val name: String, val address: String, val distance: String)
    
    data class NarrationResult(
        val spot_name: String,
        val level: String,
        val narration: String,
        val qa: Map<String, String>?
    )
    
    data class QAResult(val answer: String, val source: String, val spot_name: String)
    
    interface LocationCallback {
        fun onSpotFound(scenic: ScenicSpotInfo, subSpot: SubSpotInfo)
        fun onNotInScenicArea(pois: List<POI>)
        fun onError(msg: String)
    }
    
    interface NarrationCallback {
        fun onNarration(result: NarrationResult)
        fun onError(msg: String)
    }
    
    interface QACallback {
        fun onAnswer(result: QAResult)
        fun onError(msg: String)
    }
}
```

## 第四步：主 Activity 串联

```kotlin
// MainActivity.kt
class MainActivity : AppCompatActivity() {
    
    private lateinit var glassManager: GlassConnectionManager
    private lateinit var locationService: LocationService
    private var currentSpotId: String? = null
    private var currentSubSpotId: String? = null
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        
        glassManager = GlassConnectionManager(this)
        locationService = LocationService(this)
        
        // 1. 连接眼镜
        connectGlass()
        
        // 2. 开始定位
        startLocationTracking()
    }
    
    private fun connectGlass() {
        // 需要先通过 Rokid AI App 获取 token
        // 具体鉴权流程参考 Rokid 官方文档
        val token = getAuthToken() // 你的鉴权逻辑
        
        glassManager.connect(token, object : GlassConnectionManager.ConnectionListener {
            override fun onCxrLinkChanged(connected: Boolean) {
                runOnUiThread { updateStatus("CXR链路: ${if (connected) "已连接" else "断开"}") }
            }
            
            override fun onGlassConnected(connected: Boolean) {
                runOnUiThread { updateStatus("眼镜: ${if (connected) "已连接" else "断开"}") }
            }
        })
    }
    
    private fun startLocationTracking() {
        // 检查定位权限
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.ACCESS_FINE_LOCATION), 100)
            return
        }
        
        // 每5秒查询一次位置
        locationService.start(5000, object : LocationService.LocationCallback {
            override fun onSpotFound(scenic: LocationService.ScenicSpotInfo, subSpot: LocationService.SubSpotInfo) {
                // 发现景点，获取讲解词
                if (subSpot.id != currentSubSpotId) {
                    currentSubSpotId = subSpot.id
                    currentSpotId = scenic.id
                    
                    runOnUiThread {
                        updateStatus("📍 ${scenic.name} > ${subSpot.name}")
                    }
                    
                    // 获取讲解词
                    locationService.getNarration(scenic.id, subSpot.id, 2,
                        object : LocationService.NarrationCallback {
                            override fun onNarration(result: LocationService.NarrationResult) {
                                runOnUiThread {
                                    // 推送到眼镜
                                    glassManager.showOnGlass(result.narration, result.spot_name)
                                    // 同时在手机上显示
                                    updateNarration(result.narration)
                                }
                            }
                            
                            override fun onError(msg: String) {
                                runOnUiThread { updateStatus("❌ $msg") }
                            }
                        })
                }
            }
            
            override fun onNotInScenicArea(pois: List<LocationService.POI>) {
                currentSubSpotId = null
                runOnUiThread {
                    updateStatus("不在景区内")
                    if (pois.isNotEmpty()) {
                        updateStatus("附近: ${pois.joinToString(", ") { it.name }}")
                    }
                }
            }
            
            override fun onError(msg: String) {
                runOnUiThread { updateStatus("⚠️ $msg") }
            }
        })
    }
    
    private fun updateStatus(text: String) {
        findViewById<TextView>(R.id.tvStatus)?.text = text
    }
    
    private fun updateNarration(text: String) {
        findViewById<TextView>(R.id.tvNarration)?.text = text
    }
    
    override fun onDestroy() {
        super.onDestroy()
        locationService.stop()
        glassManager.closeOnGlass()
    }
}
```

## 第五步：布局文件

```xml
<!-- res/layout/activity_main.xml -->
<?xml version="1.0" encoding="utf-8"?>
<LinearLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:orientation="vertical"
    android:padding="16dp"
    android:background="#1a1a2e">

    <!-- 状态栏 -->
    <TextView
        android:id="@+id/tvGlassStatus"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="眼镜: 未连接"
        android:textColor="#ff6b6b"
        android:textSize="14sp" />

    <TextView
        android:id="@+id/tvStatus"
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:text="等待定位..."
        android:textColor="#4ecdc4"
        android:textSize="16sp"
        android:layout_marginTop="8dp" />

    <!-- 讲解内容 -->
    <ScrollView
        android:layout_width="match_parent"
        android:layout_height="0dp"
        android:layout_weight="1"
        android:layout_marginTop="16dp">

        <TextView
            android:id="@+id/tvNarration"
            android:layout_width="match_parent"
            android:layout_height="wrap_content"
            android:text="讲解内容将在这里显示..."
            android:textColor="#ffffff"
            android:textSize="16sp"
            android:lineSpacingMultiplier="1.4" />
    </ScrollView>

    <!-- 控制按钮 -->
    <LinearLayout
        android:layout_width="match_parent"
        android:layout_height="wrap_content"
        android:orientation="horizontal"
        android:layout_marginTop="16dp">

        <Button
            android:id="@+id/btnLevel1"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:text="基础"
            android:layout_marginEnd="4dp" />

        <Button
            android:id="@+id/btnLevel2"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:text="标准"
            android:layout_marginEnd="4dp" />

        <Button
            android:id="@+id/btnLevel3"
            android:layout_width="0dp"
            android:layout_height="wrap_content"
            android:layout_weight="1"
            android:text="深度" />
    </LinearLayout>
</LinearLayout>
```

## 权限清单

```xml
<!-- AndroidManifest.xml -->
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
<uses-permission android:name="android.permission.BLUETOOTH" />
<uses-permission android:name="android.permission.BLUETOOTH_ADMIN" />
<!-- Android 12+ -->
<uses-permission android:name="android.permission.BLUETOOTH_SCAN" />
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />
```

## 高德 Key 修复

你当前的 Key 报 `USERKEY_PLAT_NOMATCH`，需要：

1. 登录 https://lbs.amap.com/
2. 进入「应用管理」→ 找到你的应用
3. 在「服务」中添加「Web服务」类型的 Key
4. 或者创建一个新应用，选择「Web服务」类型

REST API 调用需要的是 **Web 服务** 类型的 Key，不是 JS API 或 Android SDK 的 Key。

## 部署后端

后端需要部署到公网可访问的服务器。推荐方案：

```bash
# 方案1: 云服务器（阿里云/腾讯云）
# 把 backend/ 目录上传到服务器
pip install flask flask-cors requests
python3 server.py

# 方案2: ngrok 本地测试（开发阶段）
# 安装 ngrok 后：
ngrok http 5000
# 获得公网 URL 如 http://xxxx.ngrok.io
```

然后修改 Android 代码中的 `baseUrl` 为实际的服务器地址。
