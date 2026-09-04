import 'package:flutter/material.dart';

import 'constants.dart';

/// Material You 动态配色主题工厂：
/// 以种子色生成完整 ColorScheme，深浅色自适应，全部组件只读 colorScheme。
class AppTheme {
  static ThemeData light(int seed) => _build(Brightness.light, seed);
  static ThemeData dark(int seed) => _build(Brightness.dark, seed);

  static ThemeData _build(Brightness brightness, int seed) {
    final scheme = ColorScheme.fromSeed(
      seedColor: Color(seed),
      brightness: brightness,
    );
    return ThemeData(
      colorScheme: scheme,
      useMaterial3: true,
      scaffoldBackgroundColor: scheme.surface,
      // 全局字体：调小调细（非老年机）
      textTheme: const TextTheme(
        displayLarge: TextStyle(fontSize: 34, fontWeight: FontWeight.w600),
        headlineLarge: TextStyle(fontSize: 26, fontWeight: FontWeight.w600),
        headlineMedium: TextStyle(fontSize: 22, fontWeight: FontWeight.w600),
        titleLarge: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
        titleMedium: TextStyle(fontSize: 15, fontWeight: FontWeight.w500),
        bodyLarge: TextStyle(fontSize: 14, fontWeight: FontWeight.w400),
        bodyMedium: TextStyle(fontSize: 13, fontWeight: FontWeight.w400),
        bodySmall: TextStyle(fontSize: 12, fontWeight: FontWeight.w400),
        labelLarge: TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
        labelMedium: TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
        labelSmall: TextStyle(fontSize: 11, fontWeight: FontWeight.w400),
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        titleTextStyle: TextStyle(
          color: scheme.onSurface,
          fontSize: 17,
          fontWeight: FontWeight.w600,
        ),
      ),
      cardTheme: CardTheme(
        elevation: 0,
        color: scheme.surfaceContainerHighest,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        margin: EdgeInsets.zero,
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          textStyle: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500),
          padding: const EdgeInsets.symmetric(vertical: 12),
        ),
      ),
      dialogTheme: DialogTheme(
        backgroundColor: scheme.surfaceContainerHighest,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      ),
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: scheme.surfaceContainerLow,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
        ),
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    );
  }
}

/// 状态语义色（跟随主题）
class StateColors {
  final Color delivering;
  final Color signed;
  final Color problem;
  final Color transporting;

  StateColors.of(ColorScheme scheme)
      : delivering = scheme.primary,
        signed = scheme.tertiary,
        problem = scheme.error,
        transporting = scheme.secondary;
}

Color companyColor(String code) {
  final hex = companyColorOf(code).replaceFirst('#', '');
  return Color(int.parse('FF$hex', radix: 16));
}

String stateLabel(String state) {
  switch (state) {
    case 'signed':
      return '已签收';
    case 'delivering':
      return '派送中';
    case 'problem':
      return '异常';
    default:
      return '运输中';
  }
}
