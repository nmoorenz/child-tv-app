plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "tv.childtv.app"
    compileSdk = 34

    defaultConfig {
        applicationId = "tv.childtv.app"
        minSdk = 21
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
    }

    compileOptions {
        isCoreLibraryDesugaringEnabled = true
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    signingConfigs {
        // Fixed key so every build signs identically — updates install over the old
        // app without needing to uninstall first. (Standard debug credentials.)
        getByName("debug") {
            storeFile = file("debug.keystore")
            storePassword = "android"
            keyAlias = "androiddebugkey"
            keyPassword = "android"
        }
    }

    buildTypes {
        getByName("debug") {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("debug")
        }
        getByName("release") {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.fragment:fragment-ktx:1.8.2")
    implementation("androidx.leanback:leanback:1.0.0")
    implementation("com.github.bumptech.glide:glide:4.16.0")

    // Native playback: ExoPlayer fed a specific low-res stream we extract on-device.
    implementation("androidx.media3:media3-exoplayer:1.3.1")
    implementation("androidx.media3:media3-ui:1.3.1")
    implementation("androidx.media3:media3-datasource-okhttp:1.3.1")
    // LibreTube's NewPipeExtractor fork, pinned to its NEWEST commit (e821b96,
    // 2026-08-19): "Allow extraction of SABR-only streams" + "Use visionOS client for
    // streaming data (ANDROID client recently started to require poTokens)".
    // Context: YouTube (mid-Aug 2026) began requiring poTokens on the ANDROID/IOS
    // clients and enforcing SABR, breaking on-device extraction — this currently breaks
    // LibreTube too. Its shipped pin (76e7ea7) predates this fix; e821b96 is the fresh
    // fix attempt, not yet in a LibreTube release, so it's UNPROVEN. When LibreTube
    // plays again, match its libs.versions.toml `newpipeextractor` commit. Our bare
    // ExoPlayer only plays progressive URLs, so this hinges on the visionOS client still
    // returning non-SABR URLs.
    implementation("com.github.libre-tube:NewPipeExtractor:e821b96")
    // Runtime dependency for the fork's SABR handling (generated protobuf classes need
    // the javalite runtime). Usually pulled transitively; declared explicitly to match
    // LibreTube and avoid a NoClassDefFoundError at playback time. Same version they pin.
    implementation("com.google.protobuf:protobuf-javalite:4.33.5")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")

    // Back-fills modern Java APIs onto old Android. The "_nio" variant is REQUIRED
    // by NewPipeExtractor for minSdk < 33 (covers URLDecoder.decode(String, Charset),
    // which only exists natively on Android 13+). Same version NewPipe itself uses.
    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs_nio:2.1.5")
}
