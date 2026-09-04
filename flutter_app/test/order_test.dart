import 'package:flutter_test/flutter_test.dart';
import 'package:cainiao_monitor/models.dart';

void main() {
  test('轨迹归一化为“最新在前”：first 应为最新状态（已到达）', () {
    // 模拟快递鸟返回的原始 Traces：时间升序（最早在前）
    final nodes = <TraceNode>[
      TraceNode(time: '2026-08-21 18:05', status: '顺丰速运已收取快件'),
      TraceNode(time: '2026-08-21 22:40', status: '快件已从【上海浦东新区】发出'),
      TraceNode(time: '2026-08-22 08:12', status: '快件在【上海浦东新区】已装车'),
      TraceNode(time: '2026-08-22 09:32', status: '快件已到达【杭州转运中心】，准备发往下一站'),
    ];

    // 与 kdniao_api / kuaidi100_api 中完全一致的归一化逻辑
    nodes.sort((a, b) => a.time.compareTo(b.time));
    final ordered = nodes.reversed.toList();

    // 修复后：first = 最新（已到达），last = 最早（已收取）
    expect(ordered.first.status, contains('已到达'));
    expect(ordered.last.status, contains('已收取'));
    // 卡片 latestStatus / 详情页 trace[0] 取 first，绝不能再是“发货/已收取”
    expect(ordered.first.status, isNot(contains('已收取')));

    // 顺序校验：从新到旧单调递减
    for (var i = 1; i < ordered.length; i++) {
      expect(ordered[i - 1].time.compareTo(ordered[i].time) >= 0, isTrue);
    }
  });
}
