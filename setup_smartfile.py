#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SmartFile AI - Project Generator
"""

import os
from pathlib import Path

ROOT = Path("SmartFileAI")
FILES = {}

FILES["settings.gradle.kts"] = '''
pluginManagement {
    repositories { google(); mavenCentral(); gradlePluginPortal() }
}
dependencyResolutionManagement {
    repositories { google(); mavenCentral() }
}
rootProject.name = "SmartFile AI"
include(":app")
'''

FILES["build.gradle.kts"] = '''
plugins {
    id("com.android.application") version "8.5.2" apply false
    id("org.jetbrains.kotlin.android") version "1.9.24" apply false
    id("org.jetbrains.kotlin.plugin.compose") version "1.9.24" apply false
}
'''

FILES["gradle.properties"] = '''
org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
android.useAndroidX=true
kotlin.code.style=official
android.nonTransitiveRClass=true
'''

FILES["app/build.gradle.kts"] = '''
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "com.smartfile.ai"
    compileSdk = 34
    defaultConfig {
        applicationId = "com.smartfile.ai"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "0.1.0"
    }
    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    buildFeatures { compose = true }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.4")
    implementation("androidx.activity:activity-compose:1.9.1")
    implementation(platform("androidx.compose:compose-bom:2024.09.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.navigation:navigation-compose:2.8.0")
    implementation("androidx.datastore:datastore-preferences:1.1.1")
}
'''

FILES["app/proguard-rules.pro"] = '''
-keep class com.smartfile.ai.** { *; }
'''

FILES["app/src/main/AndroidManifest.xml"] = '''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />
    <uses-permission android:name="android.permission.READ_MEDIA_VIDEO" />
    <uses-permission android:name="android.permission.READ_MEDIA_AUDIO" />
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" android:maxSdkVersion="32" />
    <uses-permission android:name="android.permission.INTERNET" />
    <application
        android:name=".SmartFileApp"
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:supportsRtl="true"
        android:theme="@style/Theme.SmartFileAI">
        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
'''

FILES["app/src/main/java/com/smartfile/ai/SmartFileApp.kt"] = '''
package com.smartfile.ai

import android.app.Application
import com.smartfile.ai.core.Prefs

class SmartFileApp : Application() {
    override fun onCreate() {
        super.onCreate()
        Prefs.init(this)
    }
}
'''

FILES["app/src/main/java/com/smartfile/ai/MainActivity.kt"] = '''
package com.smartfile.ai

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.navigation.compose.*
import com.smartfile.ai.core.Permissions
import com.smartfile.ai.nav.BottomNavBar
import com.smartfile.ai.nav.Screen
import com.smartfile.ai.ui.ai.AiScreen
import com.smartfile.ai.ui.files.FilesScreen
import com.smartfile.ai.ui.home.HomeScreen
import com.smartfile.ai.ui.profile.ProfileScreen
import com.smartfile.ai.ui.theme.BgDeep
import com.smartfile.ai.ui.theme.SmartFileTheme
import com.smartfile.ai.ui.tools.ToolsScreen
import com.smartfile.ai.ui.welcome.WelcomeScreen

class MainActivity : ComponentActivity() {
    private val permLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            SmartFileTheme {
                SmartFileRoot(onRequestPerms = { permLauncher.launch(Permissions.media) })
            }
        }
    }
}

@Composable
fun SmartFileRoot(onRequestPerms: () -> Unit) {
    var showWelcome by remember { mutableStateOf(true) }
    LaunchedEffect(Unit) { onRequestPerms() }

    if (showWelcome) {
        WelcomeScreen(onReady = { showWelcome = false })
        return
    }

    val nav = rememberNavController()
    val items = listOf(Screen.Home, Screen.Files, Screen.AI, Screen.Tools, Screen.Profile)

    Scaffold(
        containerColor = Color.Transparent,
        bottomBar = { BottomNavBar(nav, items) }
    ) { pad ->
        Box(
            Modifier
                .fillMaxSize()
                .background(Brush.verticalGradient(listOf(Color(0xFF140E2A), BgDeep, Color(0xFF06060C))))
                .padding(pad)
        ) {
            NavHost(nav, startDestination = Screen.Home.route) {
                composable(Screen.Home.route) { HomeScreen(nav) }
                composable(Screen.Files.route) { FilesScreen() }
                composable(Screen.AI.route) { AiScreen() }
                composable(Screen.Tools.route) { ToolsScreen(nav) }
                composable(Screen.Profile.route) { ProfileScreen(nav) }
            }
        }
    }
}
'''

FILES["app/src/main/java/com/smartfile/ai/core/Prefs.kt"] = '''
package com.smartfile.ai.core

import android.content.Context
import android.content.SharedPreferences

object Prefs {
    private lateinit var sp: SharedPreferences
    fun init(ctx: Context) {
        sp = ctx.getSharedPreferences("smartfile_prefs", Context.MODE_PRIVATE)
    }
    var isPro: Boolean
        get() = sp.getBoolean("is_pro", false)
        set(v) = sp.edit().putBoolean("is_pro", v).apply()
    var userName: String
        get() = sp.getString("user", "Friend") ?: "Friend"
        set(v) = sp.edit().putString("user", v).apply()
}
'''

FILES["app/src/main/java/com/smartfile/ai/core/Permissions.kt"] = '''
package com.smartfile.ai.core

import android.Manifest
import android.os.Build

object Permissions {
    val media: Array<String> = when {
        Build.VERSION.SDK_INT >= 33 -> arrayOf(
            Manifest.permission.READ_MEDIA_IMAGES,
            Manifest.permission.READ_MEDIA_VIDEO,
            Manifest.permission.READ_MEDIA_AUDIO
        )
        else -> arrayOf(
            Manifest.permission.READ_EXTERNAL_STORAGE,
            Manifest.permission.WRITE_EXTERNAL_STORAGE
        )
    }
}
'''

FILES["app/src/main/java/com/smartfile/ai/core/Logo.kt"] = '''
package com.smartfile.ai.core

import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.*
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.*
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlin.math.cos
import kotlin.math.sin

@Composable
fun RLogo(
    modifier: Modifier = Modifier,
    size: androidx.compose.ui.unit.Dp = 140.dp,
    animated: Boolean = true
) {
    val t = rememberInfiniteTransition(label = "logo")
    val rotation by t.animateFloat(
        0f, 360f,
        infiniteRepeatable(tween(6000, easing = LinearEasing)),
        label = "rot"
    )
    val pulse by t.animateFloat(
        0.85f, 1f,
        infiniteRepeatable(tween(1800, easing = FastOutSlowInEasing), RepeatMode.Reverse),
        label = "pulse"
    )

    Box(modifier.size(size), contentAlignment = Alignment.Center) {
        Canvas(Modifier.fillMaxSize()) {
            val c = Offset(this.size.width / 2f, this.size.height / 2f)
            val r = this.size.minDimension / 2f * 0.9f
            drawCircle(
                brush = Brush.radialGradient(
                    listOf(Color(0x553B82F6), Color(0x225C2D91), Color.Transparent),
                    center = c, radius = r * 1.4f
                ),
                radius = r * 1.4f, center = c
            )
            drawCircle(
                brush = Brush.sweepGradient(
                    listOf(
                        Color(0xFF6D5FFF), Color(0xFF00E5FF),
                        Color(0xFFB24BF3), Color(0xFF6D5FFF)
                    ),
                    center = c
                ),
                radius = r * pulse, center = c,
                style = Stroke(width = 4.dp.toPx())
            )
            repeat(3) { i ->
                val a = Math.toRadians((rotation + i * 120f).toDouble())
                drawCircle(
                    Color(0xFF00E5FF),
                    radius = 4.dp.toPx(),
                    center = Offset(
                        c.x + cos(a).toFloat() * r * pulse,
                        c.y + sin(a).toFloat() * r * pulse
                    )
                )
            }
        }
        Text(
            text = "R",
            fontSize = (size.value * 0.55f).sp,
            fontWeight = FontWeight.Black,
            style = TextStyle(
                brush = Brush.linearGradient(
                    listOf(Color.White, Color(0xFF9F8BFF), Color(0xFF00E5FF))
                )
            )
        )
        Text(
            text = "AI",
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .offset(x = (-size * 0.13f), y = (-size * 0.16f)),
            fontSize = (size.value * 0.14f).sp,
            fontWeight = FontWeight.Bold,
            style = TextStyle(
                brush = Brush.linearGradient(
                    listOf(Color(0xFF00E5FF), Color(0xFFB24BF3))
                )
            )
        )
    }
}
'''

FILES["app/src/main/java/com/smartfile/ai/nav/BottomNav.kt"] = '''
package com.smartfile.ai.nav

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import androidx.navigation.compose.currentBackStackEntryAsState
import com.smartfile.ai.ui.theme.AccentCyan
import com.smartfile.ai.ui.theme.PrimaryPurple
import com.smartfile.ai.ui.theme.TextSecondary

sealed class Screen(val route: String, val icon: ImageVector) {
    data object Home    : Screen("home", Icons.Outlined.Home)
    data object Files   : Screen("files", Icons.Outlined.Folder)
    data object AI      : Screen("ai", Icons.Outlined.AutoAwesome)
    data object Tools   : Screen("tools", Icons.Outlined.Build)
    data object Profile : Screen("profile", Icons.Outlined.Person)
}

@Composable
fun BottomNavBar(nav: NavHostController, items: List<Screen>) {
    val entry by nav.currentBackStackEntryAsState()
    val current = entry?.destination?.route
    Box(
        Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 12.dp)
            .clip(RoundedCornerShape(28.dp))
            .background(Brush.linearGradient(listOf(Color(0xCC1A1A2E), Color(0xCC0F0F1A))))
    ) {
        NavigationBar(containerColor = Color.Transparent, tonalElevation = 0.dp) {
            items.forEach { s ->
                val sel = current == s.route
                NavigationBarItem(
                    selected = sel,
                    onClick = {
                        if (!sel) nav.navigate(s.route) {
                            popUpTo(nav.graph.startDestinationId) { saveState = true }
                            launchSingleTop = true
                            restoreState = true
                        }
                    },
                    icon = { Icon(s.icon, null, tint = if (sel) AccentCyan else TextSecondary) },
                    colors = NavigationBarItemDefaults.colors(
                        indicatorColor = PrimaryPurple.copy(alpha = 0.25f)
                    )
                )
            }
        }
    }
}
'''

FILES["app/src/main/java/com/smartfile/ai/ui/theme/Color.kt"] = '''
package com.smartfile.ai.ui.theme

import androidx.compose.ui.graphics.Color

val BgDeep        = Color(0xFF0A0A12)
val BgSurface     = Color(0xFF12121C)
val GlassCard     = Color(0x1AFFFFFF)
val GlassBorder   = Color(0x33FFFFFF)
val PrimaryPurple = Color(0xFF6D5FFF)
val AccentCyan    = Color(0xFF00E5FF)
val AccentPink    = Color(0xFFB24BF3)
val TextPrimary   = Color(0xFFF5F5FA)
val TextSecondary = Color(0xFF9A9AB0)
'''

FILES["app/src/main/java/com/smartfile/ai/ui/theme/Theme.kt"] = '''
package com.smartfile.ai.ui.theme

import android.app.Activity
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

private val DarkScheme = darkColorScheme(
    primary = PrimaryPurple,
    secondary = AccentCyan,
    tertiary = AccentPink,
    background = BgDeep,
    surface = BgSurface,
    onPrimary = Color.White,
    onBackground = TextPrimary,
    onSurface = TextPrimary
)

@Composable
fun SmartFileTheme(darkTheme: Boolean = true, content: @Composable () -> Unit) {
    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = Color.Transparent.toArgb()
            window.navigationBarColor = Color.Transparent.toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = false
        }
    }
    MaterialTheme(colorScheme = DarkScheme, content = content)
}
'''

FILES["app/src/main/java/com/smartfile/ai/ui/theme/Glass.kt"] = '''
package com.smartfile.ai.ui.theme

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.unit.dp

fun Modifier.glassCard(radius: Int = 22): Modifier = this
    .clip(RoundedCornerShape(radius.dp))
    .background(Brush.linearGradient(listOf(GlassCard.copy(alpha = 0.12f), GlassCard.copy(alpha = 0.04f))))
    .border(
        width = 1.dp,
        brush = Brush.linearGradient(listOf(GlassBorder.copy(alpha = 0.35f), GlassBorder.copy(alpha = 0.05f))),
        shape = RoundedCornerShape(radius.dp)
    )
'''

FILES["app/src/main/java/com/smartfile/ai/ui/welcome/WelcomeScreen.kt"] = '''
package com.smartfile.ai.ui.welcome

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.smartfile.ai.core.RLogo
import com.smartfile.ai.ui.theme.*
import kotlinx.coroutines.delay

@Composable
fun WelcomeScreen(onReady: () -> Unit) {
    var visible by remember { mutableStateOf(false) }
    val scale by animateFloatAsState(
        targetValue = if (visible) 1f else 0.6f,
        animationSpec = spring(dampingRatio = 0.55f, stiffness = 180f),
        label = "scale"
    )
    val alpha by animateFloatAsState(
        targetValue = if (visible) 1f else 0f,
        animationSpec = tween(900),
        label = "alpha"
    )
    LaunchedEffect(Unit) {
        visible = true
        delay(2600)
        onReady()
    }
    Box(
        modifier = Modifier.fillMaxSize().background(
            Brush.radialGradient(listOf(Color(0xFF1A1035), BgDeep, Color(0xFF000000)))
        ),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.fillMaxWidth().padding(32.dp).scale(scale).alpha(alpha)
        ) {
            RLogo(size = 170.dp)
            Spacer(Modifier.height(36.dp))
            Text("SmartFile AI", color = TextPrimary, fontSize = 26.sp, fontWeight = FontWeight.Bold, textAlign = TextAlign.Center)
            Spacer(Modifier.height(10.dp))
            Text("Your Files. Your AI.\\nOne Smart Workspace.", color = TextSecondary, fontSize = 14.sp, textAlign = TextAlign.Center)
            Spacer(Modifier.height(60.dp))
            CircularProgressIndicator(color = AccentCyan, strokeWidth = 2.5.dp, modifier = Modifier.size(26.dp))
        }
        Text(
            "SmartFile AI  •  v0.1.0",
            color = TextSecondary.copy(alpha = 0.6f),
            fontSize = 11.sp,
            modifier = Modifier.align(Alignment.BottomCenter).padding(bottom = 28.dp)
        )
    }
}
'''

FILES["app/src/main/java/com/smartfile/ai/ui/home/HomeScreen.kt"] = '''
package com.smartfile.ai.ui.home

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import com.smartfile.ai.core.Prefs
import com.smartfile.ai.core.RLogo
import com.smartfile.ai.ui.theme.*

@Composable
fun HomeScreen(nav: NavHostController) {
    var command by remember { mutableStateOf("") }
    LazyColumn(
        Modifier.fillMaxSize().padding(horizontal = 20.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp)
    ) {
        item { Spacer(Modifier.height(50.dp)) }
        item { TopBar() }
        item { AiOrb() }
        item { CommandBar(command, { command = it }) { command = "" } }
        item { SectionTitle("Quick Actions") }
        item { QuickActionsRow { key ->
            when (key) {
                "compress" -> nav.navigate("image_tools")
                "resize"   -> nav.navigate("image_tools")
                "convert"  -> nav.navigate("image_tools")
                "pdf"      -> nav.navigate("pdf_tools")
                "files"    -> nav.navigate("files")
                "search"   -> nav.navigate("files")
            }
        } }
        item { Spacer(Modifier.height(80.dp)) }
    }
}

@Composable
private fun TopBar() {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) {
            Text("Welcome back", color = TextSecondary, fontSize = 13.sp)
            Text(Prefs.userName, color = TextPrimary, fontSize = 20.sp, fontWeight = FontWeight.Bold)
        }
        Box(Modifier.size(42.dp).clip(CircleShape).background(Color(0x22FFFFFF)), contentAlignment = Alignment.Center) {
            Icon(Icons.Default.Notifications, null, tint = TextPrimary)
        }
    }
}

@Composable
private fun AiOrb() {
    Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally) {
        RLogo(size = 150.dp)
        Spacer(Modifier.height(18.dp))
        Text("What can I do for you?", color = TextPrimary, fontSize = 22.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(6.dp))
        Text("AI is online", color = AccentCyan, fontSize = 12.sp)
    }
}

@Composable
private fun CommandBar(command: String, onCommand: (String) -> Unit, onSubmit: () -> Unit) {
    Box(Modifier.fillMaxWidth().height(58.dp).glassCard(30)) {
        Row(Modifier.fillMaxSize().padding(horizontal = 16.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Outlined.AutoAwesome, null, tint = AccentCyan)
            Spacer(Modifier.width(12.dp))
            Text(
                if (command.isEmpty()) "Ask anything..." else command,
                color = if (command.isEmpty()) TextSecondary else TextPrimary,
                fontSize = 14.sp,
                modifier = Modifier.weight(1f)
            )
            Icon(Icons.Outlined.Mic, null, tint = TextPrimary)
            Spacer(Modifier.width(12.dp))
            Box(
                Modifier.size(38.dp).clip(CircleShape)
                    .background(Brush.linearGradient(listOf(PrimaryPurple, AccentCyan)))
                    .clickable { onSubmit() },
                contentAlignment = Alignment.Center
            ) { Icon(Icons.Outlined.Send, null, tint = Color.White) }
        }
    }
}

@Composable
private fun SectionTitle(text: String) {
    Text(text, color = TextPrimary, fontSize = 16.sp, fontWeight = FontWeight.Bold)
}

@Composable
private fun QuickActionsRow(onClick: (String) -> Unit) {
    val actions = listOf(
        Triple("compress", "Compress", Icons.Outlined.Compress),
        Triple("resize", "Resize", Icons.Outlined.AspectRatio),
        Triple("convert", "Convert", Icons.Outlined.SwapHoriz),
        Triple("pdf", "PDF Tools", Icons.Outlined.PictureAsPdf),
        Triple("files", "Files", Icons.Outlined.Folder),
        Triple("search", "Search", Icons.Outlined.Search)
    )
    LazyRow(horizontalArrangement = Arrangement.spacedBy(14.dp)) {
        items(actions) { (key, label, icon) ->
            Column(
                Modifier.width(120.dp).glassCard(22).clickable { onClick(key) }.padding(16.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Box(
                    Modifier.size(48.dp).clip(CircleShape).background(PrimaryPurple.copy(alpha = 0.15f)),
                    contentAlignment = Alignment.Center
                ) { Icon(icon, null, tint = AccentCyan) }
                Spacer(Modifier.height(10.dp))
                Text(label, color = TextPrimary, fontSize = 13.sp)
            }
        }
    }
}
'''

FILES["app/src/main/java/com/smartfile/ai/ui/files/FilesScreen.kt"] = '''
package com.smartfile.ai.ui.files

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.smartfile.ai.ui.theme.*

@Composable
fun FilesScreen() {
    Column(Modifier.fillMaxSize().padding(20.dp)) {
        Spacer(Modifier.height(46.dp))
        Text("Files", color = TextPrimary, fontSize = 24.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(16.dp))
        Box(Modifier.fillMaxWidth().glassCard(24).padding(20.dp)) {
            Column {
                Text("Storage", color = TextSecondary, fontSize = 12.sp)
                Spacer(Modifier.height(6.dp))
                Text("128 GB / 256 GB", color = TextPrimary, fontSize = 20.sp, fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(14.dp))
                Box(Modifier.fillMaxWidth().height(10.dp).clip(CircleShape).background(Color(0x22FFFFFF))) {
                    Box(Modifier.fillMaxHeight().fillMaxWidth(0.5f).clip(CircleShape)
                        .background(Brush.horizontalGradient(listOf(PrimaryPurple, AccentCyan))))
                }
            }
        }
    }
}
'''

FILES["app/src/main/java/com/smartfile/ai/ui/ai/AiScreen.kt"] = '''
package com.smartfile.ai.ui.ai

import androidx.compose.foundation.layout.*
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.smartfile.ai.core.RLogo
import com.smartfile.ai.ui.theme.*

@Composable
fun AiScreen() {
    Column(Modifier.fillMaxSize().padding(20.dp)) {
        Spacer(Modifier.height(46.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            RLogo(size = 48.dp)
            Spacer(Modifier.width(12.dp))
            Column {
                Text("AI Assistant", color = TextPrimary, fontSize = 20.sp, fontWeight = FontWeight.Bold)
                Text("Offline • On-device", color = AccentCyan, fontSize = 11.sp)
            }
        }
        Spacer(Modifier.height(40.dp))
        Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
            Text("Ask me to compress, convert, resize, or find files.", color = TextSecondary)
        }
    }
}
'''

FILES["app/src/main/java/com/smartfile/ai/ui/tools/ToolsScreen.kt"] = '''
package com.smartfile.ai.ui.tools

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import com.smartfile.ai.ui.theme.*

@Composable
fun ToolsScreen(nav: NavHostController) {
    val tools = listOf(
        Triple("Image Tools", Icons.Outlined.Image, "image_tools"),
        Triple("PDF Tools", Icons.Outlined.PictureAsPdf, "pdf_tools"),
        Triple("Compress", Icons.Outlined.Compress, "image_tools"),
        Triple("Resize", Icons.Outlined.AspectRatio, "image_tools"),
    )
    Column(Modifier.fillMaxSize().padding(20.dp)) {
        Spacer(Modifier.height(46.dp))
        Text("Tools", color = TextPrimary, fontSize = 24.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(16.dp))
        LazyVerticalGrid(
            columns = GridCells.Fixed(2),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            items(tools) { (name, icon, route) ->
                Column(Modifier.glassCard(20).clickable { nav.navigate(route) }.padding(18.dp)) {
                    Box(
                        Modifier.size(44.dp).clip(CircleShape).background(AccentCyan.copy(alpha = 0.15f)),
                        contentAlignment = Alignment.Center
                    ) { Icon(icon, null, tint = AccentCyan) }
                    Spacer(Modifier.height(12.dp))
                    Text(name, color = TextPrimary, fontSize = 14.sp)
                }
            }
        }
    }
}
'''

FILES["app/src/main/java/com/smartfile/ai/ui/profile/ProfileScreen.kt"] = '''
package com.smartfile.ai.ui.profile

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import com.smartfile.ai.core.Prefs
import com.smartfile.ai.ui.theme.*

@Composable
fun ProfileScreen(nav: NavHostController?) {
    Column(Modifier.fillMaxSize().padding(20.dp)) {
        Spacer(Modifier.height(46.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                Modifier.size(64.dp).clip(CircleShape)
                    .background(Brush.linearGradient(listOf(PrimaryPurple, AccentCyan))),
                contentAlignment = Alignment.Center
            ) {
                Text(Prefs.userName.take(1).uppercase(), color = Color.White, fontSize = 26.sp, fontWeight = FontWeight.Bold)
            }
            Spacer(Modifier.width(14.dp))
            Column {
                Text(Prefs.userName, color = TextPrimary, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                Text(if (Prefs.isPro) "PRO" else "Free",
                    color = if (Prefs.isPro) AccentCyan else TextSecondary, fontSize = 12.sp)
            }
        }
        Spacer(Modifier.height(24.dp))
        Text("Account", color = TextPrimary, fontWeight = FontWeight.SemiBold)
        Spacer(Modifier.height(8.dp))
        Text("Settings • Language • Appearance • Privacy", color = TextSecondary, fontSize = 13.sp)
    }
}
'''

FILES["app/src/main/res/values/strings.xml"] = '''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">SmartFile AI</string>
</resources>
'''

FILES["app/src/main/res/values/themes.xml"] = '''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="Theme.SmartFileAI" parent="android:Theme.Material.NoActionBar">
        <item name="android:statusBarColor">@android:color/transparent</item>
        <item name="android:navigationBarColor">@android:color/transparent</item>
        <item name="android:windowBackground">@android:color/black</item>
    </style>
</resources>
'''

FILES["app/src/main/res/values/colors.xml"] = '''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="ic_launcher_background">#0A0A12</color>
</resources>
'''

FILES["app/src/main/res/values-fa/strings.xml"] = '''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">اسمارت‌فایل هوشمند</string>
</resources>
'''

FILES["app/src/main/res/drawable/ic_r_logo.xml"] = '''<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp" android:height="108dp"
    android:viewportWidth="108" android:viewportHeight="108">
    <path android:fillColor="#6D5FFF"
        android:pathData="M34,78 L34,30 L54,30 C64,30 70,36 70,45 C70,52 66,57 60,59 L72,78 L62,78 L52,61 L44,61 L44,78 Z M44,53 L54,53 C60,53 62,50 62,45 C62,40 60,38 54,38 L44,38 Z"/>
</vector>
'''

FILES["app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml"] = '''<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/ic_launcher_background"/>
    <foreground android:drawable="@drawable/ic_r_logo"/>
</adaptive-icon>
'''

FILES["app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml"] = '''<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/ic_launcher_background"/>
    <foreground android:drawable="@drawable/ic_r_logo"/>
</adaptive-icon>
'''

FILES[".gitignore"] = '''
*.iml
.gradle
/local.properties
/.idea
.DS_Store
/build
/captures
local.properties
'''

def write_files():
    print("Creating SmartFile AI project...")
    for path, content in FILES.items():
        full = ROOT / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content.strip() + "\\n", encoding="utf-8")
        print(f"  [OK] {path}")
    print(f"\\nDone! {len(FILES)} files created.")

if __name__ == "__main__":
    write_files()
