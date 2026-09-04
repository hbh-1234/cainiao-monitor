import 'package:flutter/material.dart';

import '../constants.dart';
import '../models.dart';
import '../theme.dart';

/// 物流详情：底部弹层（固定半屏 h=1/2 + 上下滑入滑出），适配 fold/flip/普通。
/// 注意：此处【不再使用 DraggableScrollableSheet】，避免首帧高度跳动造成的闪现，
/// 高度完全由 home_screen._detail 的 SizedBox(height: h/2) 恒定控制。
class DetailSheet extends StatelessWidget {
  final Package package;
  const DetailSheet({super.key, required this.package});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final stateColor = StateColors.of(scheme);
    final color = switch (package.state) {
      'signed' => stateColor.signed,
      'delivering' => stateColor.delivering,
      'problem' => stateColor.problem,
      _ => stateColor.transporting,
    };

    // 占满父级 SizedBox（home_screen 已固定为屏幕高 1/2），无内部动画 => 不闪现
    return Container(
      decoration: BoxDecoration(
        color: scheme.surfaceContainerLow,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
      ),
      child: Column(
        children: [
          const SizedBox(height: 10),
          Center(
            child: Container(
              width: 36,
              height: 4,
              decoration: BoxDecoration(
                color: scheme.outlineVariant,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 18, 24, 8),
            child: Row(
              children: [
                Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                    color: companyColor(package.companyCode).withOpacity(0.15),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  alignment: Alignment.center,
                  child: Text(
                    companyShortOf(package.companyCode),
                    style: TextStyle(
                      color: companyColor(package.companyCode),
                      fontWeight: FontWeight.w800,
                      fontSize: 14,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(package.companyName,
                          style: TextStyle(
                              color: scheme.onSurface,
                              fontSize: 18,
                              fontWeight: FontWeight.w700)),
                      const SizedBox(height: 2),
                      Text(package.maskedNo,
                          style: TextStyle(
                              color: scheme.onSurfaceVariant, fontSize: 13)),
                    ],
                  ),
                ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(stateLabel(package.state),
                      style: TextStyle(
                          color: color,
                          fontSize: 12,
                          fontWeight: FontWeight.w700)),
                ),
              ],
            ),
          ),
          const Divider(height: 24, indent: 24, endIndent: 24),
          Expanded(
            child: package.trace.isEmpty
                ? Center(
                    child: Text('暂无任何物流信息',
                        style: TextStyle(
                            color: scheme.onSurfaceVariant, fontSize: 14)))
                : ListView.builder(
                    padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
                    itemCount: package.trace.length,
                    itemBuilder: (context, i) {
                      final node = package.trace[i];
                      final isFirst = i == 0;
                      final isLast = i == package.trace.length - 1;
                      return _TimelineNode(
                        node: node,
                        isFirst: isFirst,
                        isLast: isLast,
                        accent: color,
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}

class _TimelineNode extends StatelessWidget {
  final TraceNode node;
  final bool isFirst;
  final bool isLast;
  final Color accent;

  const _TimelineNode({
    required this.node,
    required this.isFirst,
    required this.isLast,
    required this.accent,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            width: 20,
            child: Column(
              children: [
                Container(
                  width: 12,
                  height: 12,
                  margin: const EdgeInsets.only(top: 6),
                  decoration: BoxDecoration(
                    color: isFirst ? accent : scheme.outlineVariant,
                    shape: BoxShape.circle,
                    border: isFirst
                        ? Border.all(color: accent.withOpacity(0.4), width: 3)
                        : null,
                  ),
                ),
                if (!isLast)
                  Expanded(
                    child: Container(width: 2, color: scheme.outlineVariant),
                  ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Padding(
              padding: EdgeInsets.only(bottom: isLast ? 0 : 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(node.time,
                      style: TextStyle(
                          color: isFirst
                              ? accent
                              : scheme.onSurfaceVariant,
                          fontSize: 12,
                          fontWeight:
                              isFirst ? FontWeight.w700 : FontWeight.w500)),
                  const SizedBox(height: 4),
                  Text(node.status,
                      style: TextStyle(
                          color: scheme.onSurface,
                          fontSize: 14,
                          height: 1.4)),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
