import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../constants.dart';
import '../models.dart';
import '../services/config_store.dart';
import '../services/kdniao_api.dart';
import '../services/kuaidi100_api.dart';
import 'dart:async';
import '../theme.dart';
import 'add_sheet.dart';
import 'detail_sheet.dart';

/// 首页：包裹卡片列表 + FAB 添加 + 下拉刷新
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => HomeScreenState();
}

class HomeScreenState extends State<HomeScreen> {
  List<Package> _packages = [];
  bool _loading = false;
  bool _demo = true;
  Timer? _autoTimer;
  DateTime? _lastAutoRefresh;

  @override
  void initState() {
    super.initState();
    _load();
    _startAutoRefresh();
  }

  /// 自动刷新：每 30 秒检查一次，达到设定间隔且满足条件才真正查询。
  /// 条件：非演示模式、存在手动运单、未开启免打扰、当前未在刷新中。
  /// 间隔与免打扰均为实时读取，设置页改动后立即生效。
  void _startAutoRefresh() {
    _autoTimer?.cancel();
    _autoTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      _maybeAutoRefresh();
    });
  }

  Future<void> _maybeAutoRefresh() async {
    if (_loading || !mounted) return;
    final store = context.read<ConfigStore>();
    if (_demo) return;
    if (store.getManualPackages().isEmpty) return;
    if (store.getDoNotDisturb()) return;
    final min = store.getRefreshMin();
    final now = DateTime.now();
    if (_lastAutoRefresh != null &&
        now.difference(_lastAutoRefresh!) < Duration(minutes: min)) {
      return;
    }
    debugPrint('[auto-refresh] 触发刷新 @${now.toIso8601String()}');
    await _refresh();
  }

  @override
  void dispose() {
    _autoTimer?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    final store = context.read<ConfigStore>();
    final mode = store.getStartMode();
    final cached = store.getCachedPackages();
    if (mode == 'demo') {
      // 模拟模式：演示数据
      setState(() {
        _packages = demoPackages();
        _demo = true;
      });
    } else if (cached.isNotEmpty) {
      // 真实模式：优先展示本地缓存
      setState(() {
        _packages = cached;
        _demo = false;
      });
    } else if (store.getManualPackages().isNotEmpty) {
      // 真实模式有手动运单但无缓存，启动时主动拉取
      setState(() {
        _packages = [];
        _demo = false;
      });
      _refresh();
    } else {
      // 真实模式无缓存：空列表，等待用户添加运单
      setState(() {
        _packages = [];
        _demo = false;
      });
    }
  }

  Future<void> _refresh() async {
    final store = context.read<ConfigStore>();
    if (mounted) {
      setState(() => _loading = true);
      // 任何一次刷新（手动或自动）都重置计时基线，避免重叠触发
      _lastAutoRefresh = DateTime.now();
    }
    try {
      final items = store.getManualPackages();
      if (items.isEmpty) {
        // 无手动运单：demo 模式显示演示数据，live 模式显示空态
        final mode = store.getStartMode();
        if (mounted) {
          setState(() {
            _packages = mode == 'demo' ? demoPackages() : [];
            _demo = mode == 'demo';
          });
        }
      } else {
        final phone = store.getPhone();
        final provider = store.getProvider();
        final results = <Package>[];
        for (final item in items) {
          final mailNo = item['mail_no'] ?? '';
          // 公司代码：优先用存储的，否则按单号自动识别（避免默认顺丰误查其它快递）
          String code = item['code'] ?? 'OTHER';
          if (code == 'OTHER' || code == 'auto' || code.isEmpty) {
            code = autoDetectCompany(mailNo);
          }
          Package? pkg;
          String? errMsg;
          try {
            if (provider == 'kuaidi100') {
              pkg = await Kuaidi100Api(
                key: store.getK100Key(),
                customer: store.getK100Customer(),
              ).query(
                mailNo: mailNo,
                com: companyApiCodeOf(code),
                phone: phone,
              );
            } else {
              pkg = await KdNiaoApi(
                eBusinessId: store.getKdniaoId(),
                apiKey: store.getKdniaoKey(),
              ).query(
                mailNo: mailNo,
                shipperCode: companyKdniaoCodeOf(code),
                phone: phone,
              );
            }
          } catch (e, st) {
            // 打印完整异常，方便在模拟器环境定位 ClientException 根因
            debugPrint('查询 $mailNo 异常: $e');
            debugPrint('$st');
            errMsg = e.toString().replaceFirst(RegExp(r'^Exception: '), '');
          }
          if (pkg == null) {
            // 查询异常：仍生成一张卡片说明原因，而不是整条消失
            pkg = Package(
              mailNo: mailNo,
              companyCode: code,
              companyName: companyNameOf(code),
              latestStatus: errMsg != null && errMsg.isNotEmpty
                  ? '查询失败：$errMsg'
                  : '暂无物流信息',
              latestTime: '',
              state: 'problem',
              trace: const [],
            );
          } else if (pkg.trace.isEmpty) {
            // 查询成功但无轨迹：明确提示原因
            pkg = Package(
              mailNo: pkg.mailNo,
              companyCode: pkg.companyCode,
              companyName: pkg.companyName,
              latestStatus:
                  '暂无物流信息（快递鸟未返回轨迹，可到快递公司官网或菜鸟查询）',
              latestTime: pkg.latestTime,
              state: 'transporting',
              trace: pkg.trace,
            );
          }
          results.add(pkg);
        }
        await store.setCachedPackages(results);
        if (mounted) {
          setState(() {
            _packages = results;
            _demo = false;
          });
        }
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _add() async {
    final store = context.read<ConfigStore>();
    final added = await showModalBottomSheet<Map<String, String>>(
      context: context,
      isScrollControlled: true,
      builder: (_) => const AddPackageSheet(),
    );
    if (added != null) {
      await store.addManualPackage(added);
      if (mounted) _refresh();
    }
  }

  /// 由 CommonScaffold 的 FAB 调用，触发添加运单弹窗
  void showAddSheet() => _add();

  Future<void> _delete(Package pkg) async {
    final store = context.read<ConfigStore>();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('删除包裹'),
        content: Text('确定删除 ${pkg.maskedNo} 吗？'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('取消')),
          FilledButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('删除')),
        ],
      ),
    );
    if (confirmed == true) {
      await store.removeManualPackage(pkg.mailNo);
      if (mounted) {
        setState(() =>
            _packages = _packages.where((p) => p.mailNo != pkg.mailNo).toList());
      }
    }
  }

  void _detail(Package pkg) {
    final h = MediaQuery.of(context).size.height;
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => SizedBox(
        height: h / 2,
        child: DetailSheet(package: pkg),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return RefreshIndicator(
        onRefresh: _refresh,
        color: scheme.primary,
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('包裹监控',
                        style: TextStyle(
                            color: scheme.onSurface,
                            fontSize: 22,
                            fontWeight: FontWeight.w600)),
                    const SizedBox(height: 4),
                    Text(
                      _demo
                          ? '演示模式 · 下拉刷新切换为真实数据'
                          : '进行中 ${_packages.length} 件 · ${_loading ? '刷新中…' : '刚刚更新'}',
                      style: TextStyle(
                          color: scheme.onSurfaceVariant, fontSize: 13),
                    ),
                    const SizedBox(height: 14),
                  ],
                ),
              ),
            ),
            if (_packages.isEmpty)
              SliverFillRemaining(
                hasScrollBody: false,
                child: Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.inventory_2_outlined,
                          size: 64, color: scheme.outline),
                      const SizedBox(height: 12),
                      Text('暂无包裹',
                          style: TextStyle(
                              color: scheme.onSurfaceVariant, fontSize: 14)),
                      const SizedBox(height: 4),
                      Text('点击右下角 + 添加运单',
                          style: TextStyle(
                              color: scheme.outline, fontSize: 12)),
                    ],
                  ),
                ),
              )
            else
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 100),
                sliver: SliverList.separated(
                  itemCount: _packages.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 10),
                  itemBuilder: (context, i) => _PackageCard(
                      pkg: _packages[i],
                      onTap: () => _detail(_packages[i]),
                      onDelete: () => _delete(_packages[i])),
                ),
              ),
          ],
        ),
      );
  }
}

/// 包裹卡片（Material You 大圆角卡片 + 三点删除菜单）
class _PackageCard extends StatelessWidget {
  final Package pkg;
  final VoidCallback onTap;
  final VoidCallback onDelete;

  const _PackageCard(
      {required this.pkg, required this.onTap, required this.onDelete});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final states = StateColors.of(scheme);
    final stateColor = switch (pkg.state) {
      'signed' => states.signed,
      'delivering' => states.delivering,
      'problem' => states.problem,
      _ => states.transporting,
    };
    final badgeColor = companyColor(pkg.companyCode);

    return Material(
      color: scheme.surfaceContainerHighest,
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 14, 8, 14),
          child: Row(
            children: [
              // 公司徽章
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                  color: badgeColor.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(12),
                ),
                alignment: Alignment.center,
                child: Text(
                  companyShortOf(pkg.companyCode),
                  style: TextStyle(
                      color: badgeColor, fontWeight: FontWeight.w700,
                      fontSize: 12),
                ),
              ),
              const SizedBox(width: 10),
              // 内容
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(pkg.companyName,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                  color: scheme.onSurface,
                                  fontSize: 15,
                                  fontWeight: FontWeight.w700)),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: stateColor.withOpacity(0.12),
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Text(stateLabel(pkg.state),
                              style: TextStyle(
                                  color: stateColor,
                                  fontSize: 11,
                                  fontWeight: FontWeight.w700)),
                        ),
                        const SizedBox(width: 4),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(pkg.latestStatus,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                            color: scheme.onSurfaceVariant, fontSize: 13)),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Expanded(
                          child: Text(pkg.maskedNo,
                              style: TextStyle(
                                  color: scheme.outline, fontSize: 12)),
                        ),
                        Text(pkg.latestTime,
                            style: TextStyle(
                                color: scheme.outline, fontSize: 12)),
                      ],
                    ),
                  ],
                ),
              ),
              // 三点删除按钮: PopupMenuButton 在 Flutter 3.24.5 上有内部 bug,
              // PopupMenuItem 永远被压成 41x32dp, 文字 0 宽不可见。
              // 改用 InkWell + showModalBottomSheet, 屏幕宽 100% 显示"删除"文字。
              SizedBox(
                width: 36,
                height: 36,
                child: Material(
                  // 背景与卡片一致（卡片用 surfaceContainerHighest）
                  color: scheme.surfaceContainerHighest,
                  borderRadius: BorderRadius.circular(12),
                  child: InkWell(
                    borderRadius: BorderRadius.circular(12),
                    onTap: () => showModalBottomSheet<String>(
                      context: context,
                      backgroundColor: scheme.surfaceContainer,
                      shape: const RoundedRectangleBorder(
                        borderRadius: BorderRadius.vertical(
                          top: Radius.circular(16),
                        ),
                      ),
                      builder: (sheetCtx) => SafeArea(
                        top: false,
                        child: InkWell(
                          onTap: () {
                            Navigator.of(sheetCtx).pop('delete');
                          },
                          child: Padding(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 24, vertical: 18),
                            child: Row(
                              children: [
                                Icon(Icons.delete_outline,
                                    color: scheme.error, size: 22),
                                const SizedBox(width: 16),
                                Text(
                                  '删除',
                                  style: TextStyle(
                                    color: scheme.error,
                                    fontSize: 16,
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ).then((value) {
                      if (value == 'delete') onDelete();
                    }),
                    child: Icon(
                      Icons.more_vert,
                      color: scheme.onSurfaceVariant,
                      size: 18,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
