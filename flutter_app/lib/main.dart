import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'constants.dart';
import 'services/config_store.dart';
import 'screens/home_screen.dart';
import 'screens/settings_screen.dart';
import 'screens/welcome_screen.dart';
import 'theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const CainiaoMonitorApp());
}

/// 启动模式（首次选择）
enum StartMode { none, demo, live }

/// 主题模式三态
enum ThemeChoice { system, dark, light }

/// 应用状态（全局，Provider 分发）
class AppState extends ChangeNotifier {
  final ConfigStore store;
  ThemeChoice _choice;
  int _schemeIndex;
  bool _navExtended = true; // 侧边菜单是否展开（折叠时只显示图标）
  StartMode _startMode = StartMode.none;
  bool _ready = false;

  AppState(this.store)
      : _choice = ThemeChoice.system,
        _schemeIndex = 0;

  ThemeChoice get choice => _choice;
  int get schemeIndex => _schemeIndex;
  bool get navExtended => _navExtended;
  StartMode get startMode => _startMode;
  bool get ready => _ready;

  int get seed => colorSchemeSeedOf(_schemeIndex);

  ThemeMode get mode {
    switch (_choice) {
      case ThemeChoice.system:
        return ThemeMode.system;
      case ThemeChoice.dark:
        return ThemeMode.dark;
      default:
        return ThemeMode.light;
    }
  }

  Future<void> init() async {
    await store.init();
    // 从持久化读取初始值
    _choice = _choiceFromInt(store.getThemeChoice());
    _schemeIndex = store.getColorSchemeIndex();
    _navExtended = store.getNavExtended();
    final m = store.getStartMode();
    _startMode = m == 'demo'
        ? StartMode.demo
        : m == 'live'
            ? StartMode.live
            : StartMode.none;
    _ready = true;
    notifyListeners();
  }

  Future<void> setStartMode(StartMode m) async {
    _startMode = m;
    await store.setStartMode(m == StartMode.demo
        ? 'demo'
        : m == StartMode.live
            ? 'live'
            : 'none');
    notifyListeners();
  }

  static ThemeChoice _choiceFromInt(int v) {
    switch (v) {
      case 1:
        return ThemeChoice.dark;
      case 2:
        return ThemeChoice.light;
      default:
        return ThemeChoice.system;
    }
  }

  Future<void> setThemeChoice(ThemeChoice c) async {
    _choice = c;
    await store.setThemeChoice(c.index);
    notifyListeners();
  }

  Future<void> setSchemeIndex(int i) async {
    _schemeIndex = i;
    await store.setColorSchemeIndex(i);
    notifyListeners();
  }

  Future<void> toggleNavExtended() async {
    _navExtended = !_navExtended;
    await store.setNavExtended(_navExtended);
    notifyListeners();
  }
}

class CainiaoMonitorApp extends StatelessWidget {
  const CainiaoMonitorApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => AppState(ConfigStore())..init(),
      child: Consumer<AppState>(
        builder: (context, state, _) {
          if (!state.ready) {
            return const MaterialApp(
              debugShowCheckedModeBanner: false,
              home: Scaffold(body: Center(child: CircularProgressIndicator())),
            );
          }
          return ChangeNotifierProvider<ConfigStore>.value(
            value: state.store,
            child: MaterialApp(
              title: '包裹监控',
              debugShowCheckedModeBanner: false,
              theme: AppTheme.light(state.seed),
              darkTheme: AppTheme.dark(state.seed),
              themeMode: state.mode,
              // 首次启动（未选择模式）显示欢迎页；否则进入主框架
              home: state.startMode == StartMode.none
                  ? const WelcomeScreen()
                  : const CommonScaffold(),
            ),
          );
        },
      ),
    );
  }
}

/// 单一导航骨架（CommonScaffold）：
/// 左侧可折叠菜单（折叠只显示图标）+ 右侧内容区（仅首页）
/// 设置页为独立全屏页面，通过导航 push 进入（不与首页同层）
class CommonScaffold extends StatefulWidget {
  const CommonScaffold({super.key});

  @override
  State<CommonScaffold> createState() => _CommonScaffoldState();
}

class _CommonScaffoldState extends State<CommonScaffold> {
  int _index = 0;
  final _homeKey = GlobalKey<HomeScreenState>();

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final state = context.watch<AppState>();
    final extended = state.navExtended;

    return Scaffold(
      floatingActionButton: FloatingActionButton(
        mini: true,
        onPressed: () => _homeKey.currentState?.showAddSheet(),
        backgroundColor: scheme.primary,
        foregroundColor: scheme.onPrimary,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        child: const Icon(Icons.add, size: 20),
      ),
      body: Stack(
        children: [
          // ===== 内容层（全屏，同层切换首页/设置）=====
          // 左侧让位 72dp 给折叠态侧边栏，避免遮挡
          Positioned.fill(
            child: Padding(
              padding: const EdgeInsets.only(left: 72),
              child: IndexedStack(
                index: _index,
                children: [
                  HomeScreen(key: _homeKey),
                  const SettingsScreen(),
                ],
              ),
            ),
          ),
          // ===== 展开时的半透明遮罩（点击收起）=====
          if (extended)
            Positioned.fill(
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: () =>
                    context.read<AppState>().toggleNavExtended(),
                child: ColoredBox(
                  color: Colors.black.withOpacity(0.35),
                ),
              ),
            ),
          // ===== 侧边菜单浮层（折叠时贴在左侧，展开时浮在内容上方）=====
          Align(
            alignment: Alignment.centerLeft,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              curve: Curves.easeOut,
              width: extended ? 176 : 72,
              child: Material(
                color: scheme.surfaceContainer,
                elevation: extended ? 8 : 0,
                shadowColor: Colors.black.withOpacity(0.3),
                child: SafeArea(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      // 展开/收起按钮（居左）
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Padding(
                          padding: const EdgeInsets.all(6),
                          child: IconButton(
                            icon: Icon(extended
                                ? Icons.menu_open
                                : Icons.menu),
                            onPressed: () => context
                                .read<AppState>()
                                .toggleNavExtended(),
                            color: scheme.onSurfaceVariant,
                          ),
                        ),
                      ),
                      const SizedBox(height: 4),
                      _navItem(
                          context, Icons.local_shipping_outlined,
                          Icons.local_shipping, '快递',
                          active: _index == 0, onTap: () {
                        setState(() => _index = 0);
                        if (extended) {
                          context.read<AppState>().toggleNavExtended();
                        }
                      }),
                      _navItem(context, Icons.tune_outlined, Icons.tune,
                          '设置',
                          active: _index == 1, onTap: () {
                        setState(() => _index = 1);
                        if (extended) {
                          context.read<AppState>().toggleNavExtended();
                        }
                      }),
                      const Spacer(),
                      Padding(
                        padding: const EdgeInsets.all(12),
                        child: extended
                            ? Text('包裹监控',
                                maxLines: 2,
                                style: TextStyle(
                                    color: scheme.outline,
                                    fontSize: 11,
                                    fontWeight: FontWeight.w500))
                            : Icon(Icons.local_shipping,
                                size: 20, color: scheme.outline),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _navItem(BuildContext context, IconData icon, IconData activeIcon,
      String label,
      {required bool active, required VoidCallback onTap}) {
    final scheme = Theme.of(context).colorScheme;
    final state = context.watch<AppState>();
    final extended = state.navExtended;
    final color = active ? scheme.onSecondaryContainer : scheme.onSurfaceVariant;
    final bg = active ? scheme.secondaryContainer : Colors.transparent;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      child: Material(
        color: bg,
        borderRadius: BorderRadius.circular(12),
        child: InkWell(
          borderRadius: BorderRadius.circular(12),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 11),
            child: Row(
              children: [
                Icon(activeIcon, color: color, size: 21),
                if (extended) ...[
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(label,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                            color: color,
                            fontSize: 13,
                            fontWeight: FontWeight.w500)),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
