import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../constants.dart';
import '../main.dart';
import '../services/config_store.dart';
import '../services/kdniao_api.dart';
import '../services/kuaidi100_api.dart';

/// 设置页：三区（通用 / 风格 / 账号），Delegate 组件化
class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 40),
        children: [
          Text('设置',
              style: TextStyle(
                  color: scheme.onSurface,
                  fontSize: 24,
                  fontWeight: FontWeight.w600)),
          const SizedBox(height: 16),

          // ===== 通用 =====
          _SectionCard(
            title: '通用',
            children: [
              _DelegateSwitch(
                title: '免打扰',
                subtitle: '开启后不自动刷新',
                icon: Icons.notifications_off_outlined,
                value: context.watch<ConfigStore>().getDoNotDisturb(),
                onChanged: (v) =>
                    context.read<ConfigStore>().setDoNotDisturb(v),
              ),
              _DelegateSlider(
                title: '刷新间隔',
                icon: Icons.schedule_outlined,
                initialValue:
                    context.read<ConfigStore>().getRefreshMin().toDouble(),
                min: 1,
                max: 60,
                formatter: (v) => '${v.toInt()} 分钟',
                onChanged: (v) =>
                    context.read<ConfigStore>().setRefreshMin(v.toInt()),
              ),
            ],
          ),
          const SizedBox(height: 14),

          // ===== 风格 =====
          _SectionCard(
            title: '风格',
            children: [
              const _ThemeSelector(),
              const SizedBox(height: 4),
              const _SchemeSelector(),
            ],
          ),
          const SizedBox(height: 14),

          // ===== 账号 =====
          _SectionCard(
            title: '账号',
            children: [
              _DelegateAction(
                title: '切换模式',
                subtitle: '在模拟 / 真实接入之间切换',
                icon: Icons.swap_horiz_outlined,
                onTap: () => _switchMode(context),
              ),
              _DelegateAction(
                title: '切换服务商',
                subtitle: _providerSummary(context),
                icon: Icons.cloud_outlined,
                onTap: () => _showProviderSheet(context),
              ),
              _DelegateAction(
                title: '退出',
                subtitle: '清除本地数据',
                icon: Icons.logout,
                danger: true,
                onTap: () => _logout(context),
              ),
            ],
          ),
        ],
    );
  }

  // ---- 切换模式（回到欢迎页重新选择）----
  Future<void> _switchMode(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('切换模式'),
        content: const Text('将回到启动画面，重新选择「模拟模式」或「接入真实服务」。'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('取消')),
          FilledButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('切换')),
        ],
      ),
    );
    if (confirmed == true) {
      await context.read<AppState>().setStartMode(StartMode.none);
      // AppState 变化后 MaterialApp 的 home 自动切换回 WelcomeScreen
    }
  }

  // ---- 服务商概要（同步显示当前配置）----
  String _providerSummary(BuildContext context) {
    final p = context.read<ConfigStore>().getProvider();
    switch (p) {
      case 'kuaidi100':
        return '快递100（实时查询）';
      case 'kuaidiniao':
        return '快递鸟';
      default:
        return p;
    }
  }

  // ---- 服务商切换 ----
  Future<void> _showProviderSheet(BuildContext context) async {
    final store = context.read<ConfigStore>();
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => _ProviderSheet(store: store),
    );
    // 保存后刷新显示
    if (mounted) setState(() {});
  }

  Future<void> _logout(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('退出并清除数据'),
        content: const Text('将删除所有运单、缓存与 API 配置，确定退出？'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('取消')),
          FilledButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('退出')),
        ],
      ),
    );
    if (confirmed == true) {
      await context.read<ConfigStore>().clearPrivateData();
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(const SnackBar(content: Text('已退出，数据已清除')));
      }
    }
  }
}

/// 主题三按钮：跟随系统 / 黑暗 / 明亮
class _ThemeSelector extends StatelessWidget {
  const _ThemeSelector();

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final state = context.watch<AppState>();
    final choice = state.choice;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(4, 8, 4, 8),
          child: Text('主题',
              style: TextStyle(
                  color: scheme.onSurfaceVariant,
                  fontSize: 13,
                  fontWeight: FontWeight.w500)),
        ),
        Row(
          children: [
            _themeBtn(context, ThemeChoice.system, Icons.brightness_auto,
                '跟随系统', choice),
            const SizedBox(width: 8),
            _themeBtn(
                context, ThemeChoice.dark, Icons.dark_mode, '黑暗', choice),
            const SizedBox(width: 8),
            _themeBtn(
                context, ThemeChoice.light, Icons.light_mode, '明亮', choice),
          ],
        ),
      ],
    );
  }

  Widget _themeBtn(BuildContext context, ThemeChoice c, IconData icon,
      String label, ThemeChoice selected) {
    final scheme = Theme.of(context).colorScheme;
    final active = c == selected;
    return Expanded(
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => context.read<AppState>().setThemeChoice(c),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 10),
          decoration: BoxDecoration(
            color: active ? scheme.primaryContainer : scheme.surfaceContainerLow,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: active ? scheme.primary : scheme.outlineVariant,
              width: 1,
            ),
          ),
          child: Column(
            children: [
              Icon(icon,
                  size: 20,
                  color: active
                      ? scheme.onPrimaryContainer
                      : scheme.onSurfaceVariant),
              const SizedBox(height: 4),
              Text(label,
                  style: TextStyle(
                      fontSize: 11,
                      color: active
                          ? scheme.onPrimaryContainer
                          : scheme.onSurfaceVariant,
                      fontWeight: FontWeight.w500)),
            ],
          ),
        ),
      ),
    );
  }
}

/// 配色选择：方形按钮内一个圆圈，圆圈里三色
class _SchemeSelector extends StatelessWidget {
  const _SchemeSelector();

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final state = context.watch<AppState>();
    final current = state.schemeIndex;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(4, 8, 4, 8),
          child: Text('配色',
              style: TextStyle(
                  color: scheme.onSurfaceVariant,
                  fontSize: 13,
                  fontWeight: FontWeight.w500)),
        ),
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: List.generate(kColorSchemes.length, (i) {
            final item = kColorSchemes[i];
            final active = i == current;
            final colors = item.colors
                .map((h) => Color(int.parse('FF${h.replaceFirst('#', '')}',
                    radix: 16)))
                .toList();
            return InkWell(
              onTap: () => context.read<AppState>().setSchemeIndex(i),
              borderRadius: BorderRadius.circular(14),
              child: Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  color: scheme.surfaceContainerLow,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: active ? scheme.primary : scheme.outlineVariant,
                    width: active ? 2 : 1,
                  ),
                ),
                child: Center(
                  child: CustomPaint(
                    size: const Size(32, 32),
                    painter: _TriColorCirclePainter(colors),
                  ),
                ),
              ),
            );
          }),
        ),
      ],
    );
  }
}

/// 三色圆圈绘制器：三等分扇形
class _TriColorCirclePainter extends CustomPainter {
  final List<Color> colors;
  _TriColorCirclePainter(this.colors);

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2;
    final rect = Rect.fromCircle(center: center, radius: radius);
    final n = colors.length;
    for (var i = 0; i < n; i++) {
      final start = i * 2 * 3.1415926 / n - 3.1415926 / 2;
      final sweep = 2 * 3.1415926 / n;
      final paint = Paint()
        ..color = colors[i]
        ..style = PaintingStyle.fill;
      canvas.drawArc(rect, start, sweep, true, paint);
    }
    // 细描边
    canvas.drawCircle(
      center,
      radius,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.5
        ..color = Colors.black.withOpacity(0.2),
    );
  }

  @override
  bool shouldRepaint(covariant _TriColorCirclePainter oldDelegate) =>
      oldDelegate.colors != colors;
}

/// 服务商与 API 配置弹层
class _ProviderSheet extends StatefulWidget {
  final ConfigStore store;
  const _ProviderSheet({required this.store});

  @override
  State<_ProviderSheet> createState() => _ProviderSheetState();
}

class _ProviderSheetState extends State<_ProviderSheet> {
  late String _provider;
  late final TextEditingController _keyCtrl;
  late final TextEditingController _secretCtrl;
  late final TextEditingController _endpointCtrl;

  @override
  void initState() {
    super.initState();
    _provider = widget.store.getProvider();
    if (_provider == 'kuaidi100') {
      _keyCtrl = TextEditingController(text: widget.store.getK100Key());
      _secretCtrl =
          TextEditingController(text: widget.store.getK100Customer());
    } else {
      _keyCtrl = TextEditingController(text: widget.store.getKdniaoId());
      _secretCtrl = TextEditingController(text: widget.store.getKdniaoKey());
    }
    _endpointCtrl =
        TextEditingController(text: widget.store.getApiEndpoint());
  }

  @override
  void dispose() {
    _keyCtrl.dispose();
    _secretCtrl.dispose();
    _endpointCtrl.dispose();
    super.dispose();
  }

  void _save() {
    if (_provider == 'kuaidi100') {
      widget.store.setK100Key(_keyCtrl.text.trim());
      widget.store.setK100Customer(_secretCtrl.text.trim());
    } else {
      widget.store.setKdniaoId(_keyCtrl.text.trim());
      widget.store.setKdniaoKey(_secretCtrl.text.trim());
    }
    widget.store.setProvider(_provider);
    widget.store.setApiEndpoint(_endpointCtrl.text.trim());
    Navigator.pop(context);
    ScaffoldMessenger.of(context)
        .showSnackBar(const SnackBar(content: Text('服务商配置已保存')));
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
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
            const SizedBox(height: 16),
            Text('切换服务商',
                style: TextStyle(
                    color: scheme.onSurface,
                    fontSize: 19,
                    fontWeight: FontWeight.w600)),
            const SizedBox(height: 14),
            ..._providerOptions().map((o) => RadioListTile<String>(
                  value: o.$1,
                  groupValue: _provider,
                  onChanged: (v) => setState(() {
                    _provider = v!;
                    if (_provider == 'kuaidi100') {
                      _keyCtrl.text = widget.store.getK100Key();
                      _secretCtrl.text = widget.store.getK100Customer();
                    } else {
                      _keyCtrl.text = widget.store.getKdniaoId();
                      _secretCtrl.text = widget.store.getKdniaoKey();
                    }
                  }),
                  title: Text(o.$2,
                      style: TextStyle(
                          fontSize: 14, color: scheme.onSurface)),
                  subtitle: Text(o.$3,
                      style: TextStyle(
                          fontSize: 12, color: scheme.onSurfaceVariant)),
                  activeColor: scheme.primary,
                  dense: true,
                )),
            ...[
              const SizedBox(height: 8),
              TextField(
                controller: _keyCtrl,
                decoration: InputDecoration(
                  labelText: _provider == 'kuaidi100' ? '授权key' : 'EBusinessID',
                  hintText: 'API 密钥',
                  filled: true,
                  fillColor: scheme.surfaceContainerHighest,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide.none,
                  ),
                  contentPadding: const EdgeInsets.symmetric(
                      horizontal: 14, vertical: 12),
                ),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: _secretCtrl,
                decoration: InputDecoration(
                  labelText: _provider == 'kuaidi100' ? 'customer' : 'AppKey',
                  hintText: '密钥',
                  filled: true,
                  fillColor: scheme.surfaceContainerHighest,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide.none,
                  ),
                  contentPadding: const EdgeInsets.symmetric(
                      horizontal: 14, vertical: 12),
                ),
              ),
            ],
            const SizedBox(height: 20),
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                onPressed: _save,
                child: const Text('保存'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  List<(String, String, String)> _providerOptions() => const [
        ('kuaidi100', '快递100', '实时查询：授权key + customer'),
        ('kuaidiniao', '快递鸟', '需要 EBusinessID + AppKey'),
      ];
}

/// 设置分组卡片
class _SectionCard extends StatelessWidget {
  final String title;
  final List<Widget> children;
  const _SectionCard({required this.title, required this.children});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Material(
      color: scheme.surfaceContainerHighest,
      borderRadius: BorderRadius.circular(16),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 6, 12, 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(4, 8, 4, 4),
              child: Text(title,
                  style: TextStyle(
                      color: scheme.primary,
                      fontSize: 12,
                      fontWeight: FontWeight.w600)),
            ),
            ...children,
          ],
        ),
      ),
    );
  }
}

/// Delegate 组件基座
class _DelegateBase extends StatelessWidget {
  final IconData icon;
  final String title;
  final String? subtitle;
  final Widget trailing;
  final VoidCallback? onTap;
  final Color? iconColor;

  const _DelegateBase({
    required this.icon,
    required this.title,
    required this.trailing,
    this.subtitle,
    this.onTap,
    this.iconColor,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return ListTile(
      onTap: onTap,
      dense: true,
      leading: Container(
        width: 34,
        height: 34,
        decoration: BoxDecoration(
          color: (iconColor ?? scheme.primary).withOpacity(0.12),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Icon(icon, color: iconColor ?? scheme.primary, size: 18),
      ),
      title: Text(title,
          style: TextStyle(
              color: scheme.onSurface,
              fontSize: 14,
              fontWeight: FontWeight.w500)),
      subtitle: subtitle == null
          ? null
          : Text(subtitle!,
              style:
                  TextStyle(color: scheme.onSurfaceVariant, fontSize: 12)),
      trailing: trailing,
      contentPadding: const EdgeInsets.symmetric(horizontal: 4),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
    );
  }
}

/// 开关委托
class _DelegateSwitch extends StatelessWidget {
  final IconData icon;
  final String title;
  final String? subtitle;
  final bool value;
  final ValueChanged<bool> onChanged;

  const _DelegateSwitch({
    required this.icon,
    required this.title,
    required this.value,
    required this.onChanged,
    this.subtitle,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return _DelegateBase(
      icon: icon,
      title: title,
      subtitle: subtitle,
      trailing: Switch(
        value: value,
        onChanged: onChanged,
        activeColor: scheme.primary,
      ),
    );
  }
}

/// 滑块委托
class _DelegateSlider extends StatefulWidget {
  final IconData icon;
  final String title;
  final double initialValue;
  final double min;
  final double max;
  final String Function(double) formatter;
  final ValueChanged<double> onChanged;

  const _DelegateSlider({
    required this.icon,
    required this.title,
    required this.initialValue,
    required this.min,
    required this.max,
    required this.formatter,
    required this.onChanged,
  });

  @override
  State<_DelegateSlider> createState() => _DelegateSliderState();
}

class _DelegateSliderState extends State<_DelegateSlider> {
  late double _value;
  @override
  void initState() {
    _value = widget.initialValue;
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 34,
                height: 34,
                decoration: BoxDecoration(
                  color: scheme.primary.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(widget.icon, color: scheme.primary, size: 18),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(widget.title,
                    style: TextStyle(
                        color: scheme.onSurface,
                        fontSize: 14,
                        fontWeight: FontWeight.w500)),
              ),
              Text(widget.formatter(_value),
                  style: TextStyle(
                      color: scheme.primary,
                      fontSize: 13,
                      fontWeight: FontWeight.w500)),
            ],
          ),
          Slider(
            value: _value,
            min: widget.min,
            max: widget.max,
            divisions: (widget.max - widget.min).toInt(),
            activeColor: scheme.primary,
            inactiveColor: scheme.surfaceContainerLow,
            onChanged: (v) => setState(() => _value = v),
            onChangeEnd: (v) {
              setState(() => _value = v);
              widget.onChanged(v);
            },
          ),
        ],
      ),
    );
  }
}

/// 操作委托
class _DelegateAction extends StatelessWidget {
  final IconData icon;
  final String title;
  final String? subtitle;
  final bool danger;
  final VoidCallback onTap;
  const _DelegateAction(
      {required this.icon,
      required this.title,
      required this.onTap,
      this.subtitle,
      this.danger = false});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final color = danger ? scheme.error : scheme.primary;
    return _DelegateBase(
      icon: icon,
      title: title,
      subtitle: subtitle,
      iconColor: color,
      onTap: onTap,
      trailing: Icon(Icons.chevron_right,
          color: danger ? scheme.error : scheme.onSurfaceVariant, size: 20),
    );
  }
}
