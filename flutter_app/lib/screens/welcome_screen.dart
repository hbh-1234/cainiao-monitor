import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../main.dart';
import '../services/kuaidi100_api.dart';

/// 首次启动选择画面：快递鸟 API / 快递100 API / 模拟模式（动画切换 + 表单）
class WelcomeScreen extends StatefulWidget {
  const WelcomeScreen({super.key});

  @override
  State<WelcomeScreen> createState() => _WelcomeScreenState();
}

class _WelcomeScreenState extends State<WelcomeScreen> {
  String? _mode = 'kuaidi100'; // 'kuaidi100' / 'kdniao' / 'demo'
  final _idCtrl = TextEditingController();
  final _keyCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  bool _busy = false;
  String _error = '';

  @override
  void initState() {
    super.initState();
    // 若之前已保存过手机尾号，预填
    final app = context.read<AppState>();
    if (app.store.getPhone().isNotEmpty) {
      _phoneCtrl.text = app.store.getPhone();
    }
  }

  @override
  void dispose() {
    _idCtrl.dispose();
    _keyCtrl.dispose();
    _phoneCtrl.dispose();
    super.dispose();
  }

  Future<void> _start() async {
    final app = context.read<AppState>();
    setState(() {
      _busy = true;
      _error = '';
    });

    // 保存手机尾号（选填，快递查询鉴权用）
    await app.store.setPhone(_phoneCtrl.text.trim());

    if (_mode == 'demo') {
      await app.store.setStartMode('demo');
      await app.setStartMode(StartMode.demo);
    } else if (_mode == 'kuaidi100') {
      final key = _idCtrl.text.trim();
      final customer = _keyCtrl.text.trim();
      if (key.isEmpty || customer.isEmpty) {
        setState(() {
          _busy = false;
          _error = '请填写授权 key 和 customer';
        });
        return;
      }
      await app.store.setProvider('kuaidi100');
      await app.store.setK100Key(key);
      await app.store.setK100Customer(customer);
      await app.store.setStartMode('live');
      await app.setStartMode(StartMode.live);
    } else if (_mode == 'kdniao') {
      final id = _idCtrl.text.trim();
      final key = _keyCtrl.text.trim();
      if (id.isEmpty || key.isEmpty) {
        setState(() {
          _busy = false;
          _error = '请填写 EBusinessID 和 ApiKey';
        });
        return;
      }
      await app.store.setProvider('kuaidiniao');
      await app.store.setKdniaoId(id);
      await app.store.setKdniaoKey(key);
      await app.store.setStartMode('live');
      await app.setStartMode(StartMode.live);
    }

    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(28),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Logo
                  Center(
                    child: Container(
                      width: 64,
                      height: 64,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: scheme.primaryContainer,
                        borderRadius: BorderRadius.circular(18),
                      ),
                      child: Icon(Icons.local_shipping,
                          size: 34, color: scheme.onPrimaryContainer),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text('包裹监控',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                          color: scheme.onSurface,
                          fontSize: 22,
                          fontWeight: FontWeight.w700)),
                  const SizedBox(height: 4),
                  Text('选择接入方式开始使用',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                          color: scheme.onSurfaceVariant, fontSize: 13)),
                  const SizedBox(height: 28),

                  // 三模式卡片（动画切换选中态）
                  _ModeCard(
                    icon: Icons.cloud_outlined,
                    title: '快递100',
                    subtitle: '实时查询：授权key + customer（推荐）',
                    selected: _mode == 'kuaidi100',
                    onTap: () => setState(() => _mode = 'kuaidi100'),
                  ),
                  const SizedBox(height: 10),
                  _ModeCard(
                    icon: Icons.local_shipping_outlined,
                    title: '快递鸟',
                    subtitle: 'EBusinessID + ApiKey',
                    selected: _mode == 'kdniao',
                    onTap: () => setState(() => _mode = 'kdniao'),
                  ),
                  const SizedBox(height: 10),
                  _ModeCard(
                    icon: Icons.videogame_asset_outlined,
                    title: '模拟模式',
                    subtitle: '内置演示数据，离线体验全部功能',
                    selected: _mode == 'demo',
                    onTap: () => setState(() => _mode = 'demo'),
                  ),

                  // 模式选择后展开表单（动画）
                  AnimatedSwitcher(
                    duration: const Duration(milliseconds: 250),
                    switchInCurve: Curves.easeOut,
                    switchOutCurve: Curves.easeIn,
                    child: (_mode == 'kdniao' || _mode == 'kuaidi100')
                        ? Padding(
                            key: ValueKey('form_$_mode'),
                            padding: const EdgeInsets.only(top: 16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                TextField(
                                  controller: _idCtrl,
                                  decoration: InputDecoration(
                                    labelText: _mode == 'kuaidi100'
                                        ? '授权key'
                                        : 'EBusinessID',
                                    hintText: _mode == 'kuaidi100'
                                        ? '您的授权 key'
                                        : '您的 EBusinessID',
                                    filled: true,
                                    fillColor: scheme.surfaceContainerHighest,
                                    border: OutlineInputBorder(
                                      borderRadius: BorderRadius.circular(12),
                                      borderSide: BorderSide.none,
                                    ),
                                    contentPadding:
                                        const EdgeInsets.symmetric(
                                            horizontal: 14, vertical: 12),
                                  ),
                                ),
                                const SizedBox(height: 10),
                                TextField(
                                  controller: _keyCtrl,
                                  decoration: InputDecoration(
                                    labelText: _mode == 'kuaidi100'
                                        ? 'customer'
                                        : 'ApiKey',
                                    hintText: _mode == 'kuaidi100'
                                        ? '您的 customer'
                                        : '您的 ApiKey',
                                    filled: true,
                                    fillColor: scheme.surfaceContainerHighest,
                                    border: OutlineInputBorder(
                                      borderRadius: BorderRadius.circular(12),
                                      borderSide: BorderSide.none,
                                    ),
                                    contentPadding:
                                        const EdgeInsets.symmetric(
                                            horizontal: 14, vertical: 12),
                                  ),
                                ),
                                const SizedBox(height: 10),
                                TextField(
                                  controller: _phoneCtrl,
                                  keyboardType: TextInputType.phone,
                                  maxLength: 4,
                                  decoration: InputDecoration(
                                    labelText: '手机尾号（选填）',
                                    hintText: '部分快递查询需要，如 1234',
                                    prefixIcon: const Icon(
                                        Icons.phone_iphone,
                                        size: 20),
                                    filled: true,
                                    fillColor: scheme.surfaceContainerHighest,
                                    border: OutlineInputBorder(
                                      borderRadius: BorderRadius.circular(12),
                                      borderSide: BorderSide.none,
                                    ),
                                    contentPadding:
                                        const EdgeInsets.symmetric(
                                            horizontal: 14, vertical: 12),
                                    counterText: '',
                                  ),
                                ),
                              ],
                            ),
                          )
                        : const SizedBox.shrink(),
                  ),

                  if (_error.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    Text(_error,
                        textAlign: TextAlign.center,
                        style:
                            TextStyle(color: scheme.error, fontSize: 13)),
                  ],

                  const SizedBox(height: 20),
                  SizedBox(
                    height: 46,
                    child: FilledButton(
                      onPressed: _busy ? null : _start,
                      child: _busy
                          ? const SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Text('开始使用',
                              style: TextStyle(fontSize: 15)),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// 模式选择卡片（带选中动画）
class _ModeCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final bool selected;
  final VoidCallback onTap;

  const _ModeCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      curve: Curves.easeOut,
      decoration: BoxDecoration(
        color: selected ? scheme.primaryContainer : scheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: selected ? scheme.primary : Colors.transparent,
          width: 1.5,
        ),
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            child: Row(
              children: [
                Icon(icon,
                    size: 26,
                    color: selected
                        ? scheme.onPrimaryContainer
                        : scheme.onSurfaceVariant),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(title,
                          style: TextStyle(
                              color: selected
                                  ? scheme.onPrimaryContainer
                                  : scheme.onSurface,
                              fontSize: 15,
                              fontWeight: FontWeight.w600)),
                      const SizedBox(height: 2),
                      Text(subtitle,
                          style: TextStyle(
                              color: selected
                                  ? scheme.onPrimaryContainer
                                      .withOpacity(0.7)
                                  : scheme.onSurfaceVariant,
                              fontSize: 12)),
                    ],
                  ),
                ),
                Icon(
                  selected
                      ? Icons.radio_button_checked
                      : Icons.radio_button_unchecked,
                  size: 20,
                  color: selected
                      ? scheme.primary
                      : scheme.onSurfaceVariant,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
