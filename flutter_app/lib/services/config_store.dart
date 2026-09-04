import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models.dart';
import 'kdniao_api.dart';
import 'kuaidi100_api.dart';

/// 本地配置持久化（shared_preferences）
/// 继承 ChangeNotifier：setter 后 notify，让 watch<ConfigStore> 的 UI 同步刷新
class ConfigStore extends ChangeNotifier {
  static const _kManual = 'manual_packages';
  static const _kCached = 'cached_packages';
  static const _kPhone = 'phone';
  static const _kRefreshMin = 'refresh_min';
  static const _kThemeChoice = 'theme_choice';
  static const _kSchemeIndex = 'scheme_index';
  static const _kNavExtended = 'nav_extended';
  static const _kDnd = 'do_not_disturb';
  static const _kStartMode = 'start_mode';
  static const _kProvider = 'provider';
  static const _kApiKey = 'api_key';
  static const _kApiSecret = 'api_secret';
  static const _kApiEndpoint = 'api_endpoint';
  static const _kK100Key = 'k100_key';
  static const _kK100Customer = 'k100_customer';
  static const _kKdniaoId = 'kdniao_id';
  static const _kKdniaoKey = 'kdniao_key';

  SharedPreferences? _prefs;

  Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();
  }

  SharedPreferences get _p {
    assert(_prefs != null, 'ConfigStore.init() 未调用');
    return _prefs!;
  }

  // ---- 手动添加的运单 ----
  List<Map<String, String>> getManualPackages() {
    final raw = _p.getString(_kManual);
    if (raw == null) return [];
    return (jsonDecode(raw) as List<dynamic>)
        .map((e) => Map<String, String>.from(e as Map))
        .toList();
  }

  Future<void> addManualPackage(Map<String, String> item) async {
    final list = getManualPackages()..add(item);
    await _p.setString(_kManual, jsonEncode(list));
  }

  Future<void> removeManualPackage(String mailNo) async {
    final list = getManualPackages()
        .where((e) => e['mail_no'] != mailNo)
        .toList();
    await _p.setString(_kManual, jsonEncode(list));
  }

  // ---- 缓存包裹 ----
  List<Package> getCachedPackages() {
    final raw = _p.getString(_kCached);
    if (raw == null) return [];
    return (jsonDecode(raw) as List<dynamic>)
        .map((e) => Package.fromJson(Map<String, dynamic>.from(e as Map)))
        .toList();
  }

  Future<void> setCachedPackages(List<Package> packages) async {
    await _p.setString(
        _kCached, jsonEncode(packages.map((e) => e.toJson()).toList()));
  }

  // ---- 手机尾号 ----
  String getPhone() => _p.getString(_kPhone) ?? '';
  Future<void> setPhone(String phone) => _p.setString(_kPhone, phone);

  // ---- 主题（三态：0=跟随系统 1=黑暗 2=明亮）----
  int getThemeChoice() => _p.getInt(_kThemeChoice) ?? 0;
  Future<void> setThemeChoice(int v) => _p.setInt(_kThemeChoice, v);

  int getColorSchemeIndex() => _p.getInt(_kSchemeIndex) ?? 0;
  Future<void> setColorSchemeIndex(int v) => _p.setInt(_kSchemeIndex, v);

  bool getNavExtended() => _p.getBool(_kNavExtended) ?? false;
  Future<void> setNavExtended(bool v) => _p.setBool(_kNavExtended, v);

  // ---- 免打扰 ----
  bool getDoNotDisturb() => _p.getBool(_kDnd) ?? false;
  Future<void> setDoNotDisturb(bool v) async {
    await _p.setBool(_kDnd, v);
    notifyListeners();
  }

  // ---- 刷新间隔 ----
  int getRefreshMin() => _p.getInt(_kRefreshMin) ?? 5;
  Future<void> setRefreshMin(int v) async {
    await _p.setInt(_kRefreshMin, v);
    notifyListeners();
  }

  // ---- 启动模式（none=未选择 demo=模拟 live=真实接入）----
  String getStartMode() => _p.getString(_kStartMode) ?? 'none';
  Future<void> setStartMode(String v) async {
    await _p.setString(_kStartMode, v);
    notifyListeners();
  }

  // ---- 服务商与 API 配置 ----
  String getProvider() => _p.getString(_kProvider) ?? 'kuaidi100';
  Future<void> setProvider(String v) async {
    await _p.setString(_kProvider, v);
    notifyListeners();
  }

  String getApiKey() => _p.getString(_kApiKey) ?? '';
  Future<void> setApiKey(String v) async {
    await _p.setString(_kApiKey, v);
    notifyListeners();
  }

  String getApiSecret() => _p.getString(_kApiSecret) ?? '';
  Future<void> setApiSecret(String v) async {
    await _p.setString(_kApiSecret, v);
    notifyListeners();
  }

  String getApiEndpoint() => _p.getString(_kApiEndpoint) ?? '';
  Future<void> setApiEndpoint(String v) async {
    await _p.setString(_kApiEndpoint, v);
    notifyListeners();
  }

  // ---- 快递100 凭证（独立键，避免与快递鸟混淆）----
  // 注意：shared_preferences 存过的“空串”不会被 ?? 回退，必须显式判空，
  // 否则残留空值会让 app 发出空 key，快递100 返回“没有可用套餐”。
  String getK100Key() {
    final v = _p.getString(_kK100Key);
    return (v == null || v.isEmpty) ? Kuaidi100Api.defaultKey : v;
  }

  Future<void> setK100Key(String v) async {
    await _p.setString(_kK100Key, v);
    notifyListeners();
  }

  String getK100Customer() {
    final v = _p.getString(_kK100Customer);
    return (v == null || v.isEmpty) ? Kuaidi100Api.defaultCustomer : v;
  }

  Future<void> setK100Customer(String v) async {
    await _p.setString(_kK100Customer, v);
    notifyListeners();
  }

  // ---- 快递鸟 凭证（独立键）----
  String getKdniaoId() {
    final v = _p.getString(_kKdniaoId);
    return (v == null || v.isEmpty) ? KdNiaoApi.defaultEBusinessID : v;
  }

  Future<void> setKdniaoId(String v) async {
    await _p.setString(_kKdniaoId, v);
    notifyListeners();
  }

  String getKdniaoKey() {
    final v = _p.getString(_kKdniaoKey);
    return (v == null || v.isEmpty) ? KdNiaoApi.defaultApiKey : v;
  }

  Future<void> setKdniaoKey(String v) async {
    await _p.setString(_kKdniaoKey, v);
    notifyListeners();
  }

  // ---- 清除 ----
  Future<void> clearPrivateData() async {
    await _p.remove(_kManual);
    await _p.remove(_kCached);
    await _p.remove(_kPhone);
    notifyListeners();
  }
}
