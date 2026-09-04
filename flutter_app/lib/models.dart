/// 数据模型：包裹与物流轨迹节点
class TraceNode {
  final String time;
  final String status;
  final String? kind; // start / end / null

  const TraceNode({required this.time, required this.status, this.kind});

  factory TraceNode.fromJson(Map<String, dynamic> json) => TraceNode(
        time: json['time'] as String? ?? '',
        status: json['status'] as String? ?? '',
        kind: json['kind'] as String?,
      );

  Map<String, dynamic> toJson() => {'time': time, 'status': status, 'kind': kind};
}

class Package {
  final String mailNo;
  final String companyCode;
  final String companyName;
  final String latestStatus;
  final String latestTime;
  final String state; // transporting / delivering / signed / problem
  final List<TraceNode> trace;

  const Package({
    required this.mailNo,
    required this.companyCode,
    required this.companyName,
    required this.latestStatus,
    required this.latestTime,
    this.state = 'transporting',
    this.trace = const [],
  });

  String get maskedNo {
    if (mailNo.length <= 8) return mailNo;
    return '${mailNo.substring(0, 4)}••••${mailNo.substring(mailNo.length - 4)}';
  }

  factory Package.fromJson(Map<String, dynamic> json) => Package(
        mailNo: json['mailNo'] as String? ?? '',
        companyCode: json['companyCode'] as String? ?? '',
        companyName: json['companyName'] as String? ?? '',
        latestStatus: json['latestStatus'] as String? ?? '',
        latestTime: json['latestTime'] as String? ?? '',
        state: json['state'] as String? ?? 'transporting',
        trace: (json['trace'] as List<dynamic>? ?? [])
            .map((e) => TraceNode.fromJson(e as Map<String, dynamic>))
            .toList(),
      );

  Map<String, dynamic> toJson() => {
        'mailNo': mailNo,
        'companyCode': companyCode,
        'companyName': companyName,
        'latestStatus': latestStatus,
        'latestTime': latestTime,
        'state': state,
        'trace': trace.map((e) => e.toJson()).toList(),
      };
}
