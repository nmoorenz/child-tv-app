# Debug builds are not minified, so these are only relevant if you enable R8.
# Keep NewPipeExtractor + Rhino (uses reflection / JS engine).
-keep class org.schabi.newpipe.extractor.** { *; }
-keep class org.mozilla.javascript.** { *; }
-dontwarn org.mozilla.javascript.**
-dontwarn org.schabi.newpipe.extractor.**
