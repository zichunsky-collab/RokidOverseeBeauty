package com.rokid.cxrswithcxrl

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.HelpOutline
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.lifecycle.ViewModelProvider
import com.rokid.cxrswithcxrl.ui.theme.CXRSWithCXRLTheme
import com.rokid.cxrswithcxrl.viewmodel.MainViewModel

class MainActivity : ComponentActivity() {

    private lateinit var viewModel: MainViewModel

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { results ->
        val allGranted = results.values.all { it }
        if (allGranted) {
            viewModel.init()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        viewModel = ViewModelProvider(this)[MainViewModel::class.java]

        setContent {
            CXRSWithCXRLTheme {
                MainScreen(viewModel = viewModel)
            }
        }

        requestPermissions()
    }

    private fun requestPermissions() {
        val needed = mutableListOf<String>()
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            needed.add(Manifest.permission.ACCESS_FINE_LOCATION)
        }
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_SCAN) != PackageManager.PERMISSION_GRANTED) {
            needed.add(Manifest.permission.BLUETOOTH_SCAN)
        }
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_CONNECT) != PackageManager.PERMISSION_GRANTED) {
            needed.add(Manifest.permission.BLUETOOTH_CONNECT)
        }
        if (needed.isNotEmpty()) {
            permissionLauncher.launch(needed.toTypedArray())
        } else {
            viewModel.init()
        }
    }

    override fun onResume() {
        super.onResume()
        viewModel.onResume()
    }

    override fun onPause() {
        super.onPause()
        viewModel.onPause()
    }
}

// ─── 主界面 Compose ──────────────────────────────────

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(viewModel: MainViewModel) {
    val glassState by viewModel.glassState.collectAsState()
    val gpsState by viewModel.gpsState.collectAsState()
    val spotName by viewModel.spotName.collectAsState()
    val narration by viewModel.narration.collectAsState()
    val message by viewModel.message.collectAsState()

    var showQA by remember { mutableStateOf(false) }
    var qaInput by remember { mutableStateOf("") }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text("镜览山河", fontWeight = FontWeight.Bold)
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF1a1a2e),
                    titleContentColor = Color.White
                )
            )
        },
        containerColor = Color(0xFF0f0f23)
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // ── 状态卡片 ──────────────────────────
            StatusCard(
                title = "设备状态",
                lines = listOf(
                    glassState,
                    gpsState,
                    if (spotName.isNotEmpty()) "📍 $spotName" else null
                ).filterNotNull()
            )

            // ── 讲解内容卡片 ──────────────────────
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF16213e)),
                shape = RoundedCornerShape(12.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = "讲解内容",
                        color = Color(0xFF4ecdc4),
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = narration,
                        color = Color.White,
                        fontSize = 15.sp,
                        lineHeight = 24.sp
                    )
                }
            }

            // ── 讲解深度按钮 ──────────────────────
            Text("讲解深度", color = Color(0xFF888888), fontSize = 12.sp)
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                LevelButton("基础", modifier = Modifier.weight(1f)) { viewModel.setLevel("basic") }
                LevelButton("标准", modifier = Modifier.weight(1f)) { viewModel.setLevel("standard") }
                LevelButton("深度", modifier = Modifier.weight(1f)) { viewModel.setLevel("deep") }
            }

            // ── 功能按钮 ──────────────────────────
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                ActionButton(
                    icon = Icons.Default.CameraAlt,
                    label = "拍照",
                    modifier = Modifier.weight(1f),
                    onClick = { viewModel.takePhoto { /* 可以保存或展示 */ } }
                )
                ActionButton(
                    icon = Icons.Default.HelpOutline,
                    label = "问答",
                    modifier = Modifier.weight(1f),
                    onClick = { showQA = !showQA }
                )
                ActionButton(
                    icon = Icons.Default.LocationOn,
                    label = "刷新位置",
                    modifier = Modifier.weight(1f),
                    onClick = { com.rokid.cxrswithcxrl.utils.LocationTracker.resetSpot() }
                )
            }

            // ── 问答输入框 ──────────────────────────
            if (showQA) {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF1a1a3e)),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text("💬 语音问答", color = Color(0xFF4ecdc4), fontSize = 14.sp)
                        Spacer(modifier = Modifier.height(8.dp))
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            OutlinedTextField(
                                value = qaInput,
                                onValueChange = { qaInput = it },
                                placeholder = { Text("输入你的问题...", color = Color.Gray) },
                                modifier = Modifier.weight(1f),
                                singleLine = true,
                                colors = OutlinedTextFieldDefaults.colors(
                                    focusedTextColor = Color.White,
                                    unfocusedTextColor = Color.White,
                                    cursorColor = Color(0xFF4ecdc4)
                                )
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Button(
                                onClick = {
                                    if (qaInput.isNotBlank()) {
                                        viewModel.askQuestion(qaInput)
                                        qaInput = ""
                                    }
                                },
                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF4ecdc4))
                            ) {
                                Text("发送", color = Color.Black)
                            }
                        }
                    }
                }
            }

            // ── 错误提示 ──────────────────────────
            if (message.isNotEmpty()) {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF3e1a1a)),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text(
                        text = message,
                        color = Color(0xFFff6b6b),
                        modifier = Modifier.padding(12.dp),
                        fontSize = 13.sp
                    )
                }
            }
        }
    }
}

// ─── 组件 ──────────────────────────────────────────

@Composable
fun StatusCard(title: String, lines: List<String>) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF16213e)),
        shape = RoundedCornerShape(12.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = title,
                color = Color(0xFF4ecdc4),
                fontSize = 14.sp,
                fontWeight = FontWeight.Bold
            )
            Spacer(modifier = Modifier.height(8.dp))
            lines.forEach { line ->
                Text(
                    text = line,
                    color = Color.White,
                    fontSize = 14.sp,
                    modifier = Modifier.padding(vertical = 2.dp)
                )
            }
        }
    }
}

@Composable
fun LevelButton(text: String, modifier: Modifier = Modifier, onClick: () -> Unit) {
    Button(
        onClick = onClick,
        modifier = modifier,
        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF1a1a3e)),
        shape = RoundedCornerShape(8.dp),
        contentPadding = PaddingValues(vertical = 12.dp)
    ) {
        Text(text, color = Color(0xFF4ecdc4))
    }
}

@Composable
fun ActionButton(
    icon: ImageVector,
    label: String,
    modifier: Modifier = Modifier,
    onClick: () -> Unit
) {
    Button(
        onClick = onClick,
        modifier = modifier,
        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF1a1a3e)),
        shape = RoundedCornerShape(8.dp),
        contentPadding = PaddingValues(vertical = 12.dp)
    ) {
        Icon(icon, contentDescription = label, tint = Color(0xFF4ecdc4))
        Spacer(modifier = Modifier.width(4.dp))
        Text(label, color = Color.White, fontSize = 13.sp)
    }
}
