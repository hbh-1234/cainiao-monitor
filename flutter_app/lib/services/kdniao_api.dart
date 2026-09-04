import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';

import '../constants.dart';
import '../models.dart';

  /// 快递鸟（KDNiao）即时查询接口（RequestType 8001）
class KdNiaoApi {
  /// 默认凭证为空，需用户在欢迎页/设置页自行填入自己的 EBusinessID + ApiKey。
  static const String defaultEBusinessID = '';
  static const String defaultApiKey = '';
  static const String _host = 'api.kdniao.com';
  // 备用 IP：部分模拟器（如 MuMu）App 层 DNS 解析失败，curl 却可以，
  // 这时用 IP + Host 头能绕过域名解析。
  static const String _fallbackIp = '36.249.80.84';

  final String eBusinessId;
  final String apiKey;

  const KdNiaoApi({required this.eBusinessId, required this.apiKey});

  /// 计算 DataSign（原始 base64，不 URL 编码——发送时会手动 form 编码一次）：
  /// 1. RequestData(无空格 JSON) + ApiKey 拼接
  /// 2. MD5 加密取 hex 字符串
  /// 3. 对 hex 字符串做 Base64
  static String dataSign(String requestData, String apiKey) {
    final hex = md5.convert(utf8.encode('$requestData$apiKey')).toString();
    return base64Encode(utf8.encode(hex));
  }

  /// 即时查询物流轨迹
  Future<Package> query({
    required String mailNo,
    required String shipperCode,
    String phone = '',
  }) async {
    // 请求参数 JSON（原样参与签名）
    final params = <String, String>{
      'OrderCode': '',
      'ShipperCode': shipperCode,
      'LogisticCode': mailNo,
      if (phone.isNotEmpty) 'CustomerName': phone,
    };
    final requestData = jsonEncode(params);

    final sign = dataSign(requestData, apiKey);

    // 手动构造 form body，避免 Dart http 包二次编码导致的 %25 问题
    String enc(String s) => Uri.encodeQueryComponent(s);
    final form = StringBuffer()
      ..write('RequestData=${enc(requestData)}')
      ..write('&EBusinessID=${enc(eBusinessId)}')
      ..write('&RequestType=8001')
      ..write('&DataSign=${enc(sign)}')
      ..write('&DataType=2');

    // 先走域名；若 App 层 DNS 解析失败（如 MuMu 模拟器），fallback 到 IP + Host 头
    Map<String, dynamic> data;
    try {
      data = await _post(form.toString(), host: _host);
    } on SocketException catch (_) {
      data = await _post(form.toString(), host: _fallbackIp, headerHost: _host);
    }
    return _processData(data, shipperCode, mailNo);
  }

  /// POST 到快递鸟，支持指定 Host 头（IP 直连时使用）
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
          .postUrl(Uri.parse('https://$host/api/dist'))
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

  Package _processData(
      Map<String, dynamic> data, String shipperCode, String mailNo) {


    if (data['Success'] != true && data['Success'] != 'true') {
      throw Exception(data['Reason']?.toString() ?? '查询失败');
    }

    final apiCode = data['ShipperCode']?.toString() ?? shipperCode;
    final companyCode = _companyCodeOf(apiCode);
    final companyName = companyNameOf(companyCode);

    final traces = (data['Traces'] as List<dynamic>? ?? []);
    final nodes = traces.map((e) {
      final m = e as Map<String, dynamic>;
      return TraceNode(
        time: (m['AcceptTime']?.toString() ?? '').replaceAll('T', ' '),
        status: m['AcceptStation']?.toString() ?? m['Remark']?.toString() ?? '',
      );
    }).toList();

    // 快递鸟 Traces 默认时间升序（最早在前），统一归一化为“最新在前”，
    // 与演示数据及详情页时间线（trace[0] 高亮为最新）约定一致。
    nodes.sort((a, b) => a.time.compareTo(b.time));
    final ordered = nodes.reversed.toList();

    final latest = ordered.isNotEmpty ? ordered.first : null;
    final state = _stateOf(data['State']?.toString() ?? '');

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

  /// 快递鸟 ShipperCode -> 应用内 companyCode
  static String _companyCodeOf(String code) {
    const map = {
      'SF': 'SF', 'YTO': 'YTO', 'ZTO': 'ZTO', 'STO': 'STO',
      'YD': 'YUNDA', 'JD': 'JD', 'EMS': 'EMS', 'JTSD': 'JT',
      'YZPY': 'EMS', 'DBL': 'OTHER', 'HTKY': 'OTHER',
    };
    return map[code] ?? 'OTHER';
  }

  /// 快递鸟 State -> 应用内 state
  /// 0 在途 / 1 揽收 / 2 疑难 / 3 签收 / 4 退签 / 5 派件 / 6 退回
  static String _stateOf(String state) {
    switch (state) {
      case '3':
        return 'signed';
      case '5':
        return 'delivering';
      case '2':
      case '4':
      case '6':
        return 'problem';
      default:
        return 'transporting';
    }
  }
}
