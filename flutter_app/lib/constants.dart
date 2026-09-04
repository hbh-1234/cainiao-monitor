import 'models.dart';

/// 快递公司信息表：code -> (简称, 公司名, 快递100 com 代码, 快递鸟 ShipperCode, 品牌色)
const Map<String, List<String>> kCompanyInfo = {
  'SF': ['顺丰', '顺丰速运', 'shunfeng', 'SF', '#00B14F'],
  'YTO': ['圆通', '圆通速递', 'yuantong', 'YTO', '#2A7DE1'],
  'ZTO': ['中通', '中通快递', 'zhongtong', 'ZTO', '#F5A623'],
  'STO': ['申通', '申通快递', 'shentong', 'STO', '#D0021B'],
  'YUNDA': ['韵达', '韵达快递', 'yunda', 'YD', '#7ED321'],
  'JD': ['京东', '京东物流', 'jd', 'JD', '#E60012'],
  'EMS': ['EMS', 'EMS邮政', 'ems', 'EMS', '#1F7B4D'],
  'JT': ['极兔', '极兔速递', 'jtexpress', 'JTSD', '#5A31F4'],
  'ZT': ['中通', '中通快运', 'zhongtong', 'ZTO', '#F5A623'],
  'DHL': ['DHL', 'DHL国际', 'dhl', 'DHL', '#FFCC00'],
  'OTHER': ['快递', '其他快递', 'auto', 'auto', '#607D8B'],
};

String companyNameOf(String code) =>
    kCompanyInfo[code]?[1] ?? code;
String companyShortOf(String code) =>
    kCompanyInfo[code]?[0] ?? code;
String companyApiCodeOf(String code) =>
    kCompanyInfo[code]?[2] ?? 'auto';
String companyKdniaoCodeOf(String code) =>
    kCompanyInfo[code]?[3] ?? 'auto';
String companyColorOf(String code) =>
    kCompanyInfo[code]?[4] ?? '#607D8B';

const List<String> kCompanyCodes = [
  'SF', 'YTO', 'ZTO', 'STO', 'YUNDA', 'JD', 'EMS', 'JT', 'OTHER',
];

/// 根据运单号前缀自动识别快递公司（手输单号时默认选中，避免误用顺丰查询其他快递）
String autoDetectCompany(String mailNo) {
  final n = mailNo.trim().toUpperCase();
  if (n.isEmpty) return 'OTHER';
  if (n.startsWith('SF')) return 'SF';
  if (n.startsWith('YT')) return 'YTO'; // YT / YTO
  if (n.startsWith('ZT')) return 'ZTO'; // ZT / ZTO
  if (n.startsWith('73') || n.startsWith('75')) return 'ZTO'; // 中通常见号段
  if (n.startsWith('STO') || n.startsWith('77')) return 'STO';
  if (n.startsWith('YD') || n.startsWith('31')) return 'YUNDA';
  if (n.startsWith('JD') || n.startsWith('JB')) return 'JD';
  if (n.startsWith('EMS') || n.startsWith('EY') || n.startsWith('10')) return 'EMS';
  if (n.startsWith('JT')) return 'JT';
  return 'OTHER';
}

/// 配色方案：方形按钮内的圆圈展示三色，取第一色作为种子色生成 Material You
class ColorSchemeItem {
  final String name;
  final List<String> colors; // 三色
  const ColorSchemeItem(this.name, this.colors);
}

const List<ColorSchemeItem> kColorSchemes = [
  ColorSchemeItem('冰霜', ['#B5C5D7', '#D4B5D7', '#E8E7E9']),
  ColorSchemeItem('暖沙', ['#EBD7C6', '#D2D7B8', '#EEC8C4']),
  ColorSchemeItem('晴空', ['#8DC5F2', '#EAB2E6', '#F0F5CA']),
  ColorSchemeItem('抹茶', ['#DFE691', '#F3F1DA', '#FFFFFF']),
  ColorSchemeItem('冷灰', ['#B4C1D4', '#CFD3DD', '#FFFFFF']),
  ColorSchemeItem('薄荷', ['#ABEBC7', '#CAEBC7', '#FFFFFF']),
  ColorSchemeItem('奶油', ['#F5EAD7', '#F5D7D8', '#FFFFFF']),
  ColorSchemeItem('丁香', ['#D7CDF5', '#F5CDF0', '#FFFFFF']),
];

int colorSchemeSeedOf(int index) {
  final c = kColorSchemes[index % kColorSchemes.length].colors.first;
  return int.parse('FF${c.replaceFirst('#', '')}', radix: 16);
}

String colorSchemeNameOf(int index) =>
    kColorSchemes[index % kColorSchemes.length].name;

/// 演示数据
List<Package> demoPackages() => [
      Package(
        mailNo: 'SF1427395820135',
        companyCode: 'SF',
        companyName: '顺丰速运',
        latestStatus: '快件已到达【杭州转运中心】，准备发往下一站',
        latestTime: '2026-08-22 09:32',
        state: 'transporting',
        trace: [
          TraceNode(time: '2026-08-22 09:32', status: '快件已到达【杭州转运中心】，准备发往下一站', kind: 'end'),
          TraceNode(time: '2026-08-22 08:12', status: '快件在【上海浦东新区】已装车'),
          TraceNode(time: '2026-08-21 22:40', status: '快件已从【上海浦东新区】发出'),
          TraceNode(time: '2026-08-21 18:05', status: '顺丰速运已收取快件', kind: 'start'),
        ],
      ),
      Package(
        mailNo: 'YT7684951203498',
        companyCode: 'YTO',
        companyName: '圆通速递',
        latestStatus: '派件中，快递员正在为您派送',
        latestTime: '2026-08-22 08:45',
        state: 'delivering',
        trace: [
          TraceNode(time: '2026-08-22 08:45', status: '派件中，快递员正在为您派送', kind: 'end'),
          TraceNode(time: '2026-08-22 07:30', status: '快件已到达【杭州市西湖区】网点'),
          TraceNode(time: '2026-08-21 20:15', status: '快件在【金华转运中心】完成分拣'),
          TraceNode(time: '2026-08-21 10:00', status: '商家已发货，等待揽收', kind: 'start'),
        ],
      ),
      Package(
        mailNo: 'JT9912045612377',
        companyCode: 'JT',
        companyName: '极兔速递',
        latestStatus: '快件已签收，签收人：菜鸟驿站（代收）',
        latestTime: '2026-08-21 11:20',
        state: 'signed',
        trace: [
          TraceNode(time: '2026-08-21 11:20', status: '快件已签收，签收人：菜鸟驿站（代收）', kind: 'end'),
          TraceNode(time: '2026-08-21 09:00', status: '派件中'),
          TraceNode(time: '2026-08-20 16:30', status: '快件已到达【杭州市下城区】网点', kind: 'start'),
        ],
      ),
    ];
