import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';

import '../constants.dart';
import '../models.dart';

/// 快递100 实时查询接口（https://poll.kuaidi100.com/poll/query.do）
///
/// 签名规则（官网）：sign = MD5(param + key + customer)，结果转 32 位大写，不加 "+" 号。
/// param 为业务参数 JSON 字符串（com / num / phone / resultv2）。
class Kuaidi100Api {
  /// 默认凭证为空，需用户在欢迎页/设置页自行填入自己的 key + customer。
  static const String defaultKey = '';
  static const String defaultCustomer = '';

  static const String _host = 'poll.kuaidi100.com';
  // 备用 IP：部分模拟器（如 MuMu）App 层 DNS 解析失败，curl 却可以，
  // 这时用 IP + Host 头绕过域名解析。
  static const String _fallbackIp = '120.92.182.60';

  /// 同单号最小查询间隔（官网要求每单至少间隔半小时，否则会锁单）
  static const _minInterval = Duration(minutes: 30);
  static final Map<String, _CacheEntry> _cache = {};

  final String key;
  final String customer;

  const Kuaidi100Api({required this.key, required this.customer});

  /// 签名：MD5(param + key + customer) -> 32 位大写
  static String _sign(String param, String key, String customer) {
    final raw = '$param$key$customer';
    return md5.convert(utf8.encode(raw)).toString().toUpperCase();
  }

  /// 实时查询物流轨迹
  /// [com] 为快递100 公司编码（小写），未知时传 'auto' 启用智能判断。
  Future<Package> query({
    required String mailNo,
    required String com,
    String phone = '',
  }) async {
    // 同单号 30 分钟内直接返回缓存，避免触发快递100 锁单限制
    final cacheKey = '$mailNo@$com@$phone';
    final cached = _cache[cacheKey];
    if (cached != null &&
        DateTime.now().difference(cached.time) < _minInterval) {
      return cached.pkg;
    }

    final paramMap = <String, dynamic>{
      'com': com,
      'num': mailNo,
      if (phone.isNotEmpty) 'phone': phone,
      'resultv2': 1,
    };
    final param = jsonEncode(paramMap);
    final sign = _sign(param, key, customer);

    // 手动构造 form body，避免二次编码问题
    String enc(String s) => Uri.encodeQueryComponent(s);
    final form = StringBuffer()
      ..write('customer=${enc(customer)}')
      ..write('&param=${enc(param)}')
      ..write('&sign=${enc(sign)}');

    // 先走域名；App 层 DNS 失败时 fallback 到 IP + Host 头
    Map<String, dynamic> data;
    try {
      data = await _post(form.toString(), host: _host);
    } on SocketException catch (_) {
      data = await _post(form.toString(), host: _fallbackIp, headerHost: _host);
    }

    final pkg = _processData(data, mailNo);
    _cache[cacheKey] = _CacheEntry(DateTime.now(), pkg);
    return pkg;
  }

  Future<Map<String, dynamic>> _post(
    String body, {
    required String host,
    String? headerHost,
  }) async {
    final client = HttpClient()
      ..badCertificateCallback =
          (X509Certificate cert, String host, int port) => true;
    try {
      final req = await client
          .postUrl(Uri.parse('https://$host/poll/query.do'))
          .timeout(const Duration(seconds: 20));
      req.headers.set(
          'Content-Type', 'application/x-www-form-urlencoded;charset=utf-8');
      if (headerHost != null) {
        req.headers.set('Host', headerHost);
      }
      req.add(utf8.encode(body));

      final resp = await req.close().timeout(const Duration(seconds: 20));
      final bodyBytes =
          await resp.fold<List<int>>(<int>[], (a, b) => a..addAll(b));

      if (resp.statusCode != 200) {
        throw Exception('查询失败（HTTP ${resp.statusCode}）');
      }
      return jsonDecode(utf8.decode(bodyBytes)) as Map<String, dynamic>;
    } finally {
      client.close();
    }
  }

  Package _processData(Map<String, dynamic> data, String mailNo) {
    final status = data['status']?.toString() ?? '';
    final message = data['message']?.toString() ?? '';
    if (status != '200') {
      throw Exception(message.isNotEmpty ? message : '查询失败');
    }

    final com = data['com']?.toString() ?? '';
    final companyCode = _companyCodeOf(com);
    final companyName = companyNameOf(companyCode);

    final list = (data['data'] as List<dynamic>? ?? []);
    final nodes = list.map((e) {
      final m = e as Map<String, dynamic>;
      return TraceNode(
        time: (m['ftime']?.toString() ?? m['time']?.toString() ?? '')
            .replaceAll('T', ' '),
        status: m['context']?.toString() ?? '',
      );
    }).toList();

    // 快递100 data 默认时间升序（最早在前），统一归一化为“最新在前”，
    // 与演示数据及详情页时间线（trace[0] 高亮为最新）约定一致。
    nodes.sort((a, b) => a.time.compareTo(b.time));
    final ordered = nodes.reversed.toList();

    final latest = ordered.isNotEmpty ? ordered.first : null;
    final state = _stateOf(data['state']?.toString() ?? '');

    return Package(
      mailNo: mailNo,
      companyCode: companyCode,
      companyName: companyName,
      latestStatus: latest?.status ?? '暂无物流信息',
      latestTime: latest?.time ?? '',
      state: state,
      trace: ordered,
    );
  }

  /// 快递100 com 编码 -> 应用内 companyCode
  static String _companyCodeOf(String com) {
    const map = {
      'shunfeng': 'SF',
      'yuantong': 'YTO',
      'zhongtong': 'ZTO',
      'shentong': 'STO',
      'yunda': 'YUNDA',
      'jd': 'JD',
      'ems': 'EMS',
      'jtexpress': 'JT',
      'youzhengguonei': 'EMS',
      'tiantian': 'OTHER',
    };
    return map[com] ?? 'OTHER';
  }

  /// 快递100 state -> 应用内 state
  /// 0 在途 / 1 揽收 / 2 疑难 / 3 签收 / 4 退签 / 5 派件 / 6 退回 / 7 转投 / 8 清关
  static String _stateOf(String state) {
    switch (state) {
      case '3':
        return 'signed';
      case '5':
        return 'delivering';
      case '2':
      case '4':
      case '6':
      case '7':
        return 'problem';
      default:
        return 'transporting';
    }
  }
}

class _CacheEntry {
  final DateTime time;
  final Package pkg;
  _CacheEntry(this.time, this.pkg);
}
