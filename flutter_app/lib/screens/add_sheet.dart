import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../constants.dart';
import '../services/config_store.dart';

/// 添加运单底部弹层（自适应：移动端底部弹层）
class AddPackageSheet extends StatefulWidget {
  const AddPackageSheet({super.key});

  @override
  State<AddPackageSheet> createState() => _AddPackageSheetState();
}

class _AddPackageSheetState extends State<AddPackageSheet> {
  final _mailNoCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  String _company = 'SF';

  @override
  void initState() {
    super.initState();
    // 预填登录页保存的手机尾号，避免每次手动输入
    final store = context.read<ConfigStore>();
    if (store.getPhone().isNotEmpty) {
      _phoneCtrl.text = store.getPhone();
    }
  }

  @override
  void dispose() {
    _mailNoCtrl.dispose();
    _phoneCtrl.dispose();
    super.dispose();
  }

  /// 单号变化时自动识别快递公司（仅在尚未手动选择其它公司时自动预选）
  void _onMailNoChanged(String v) {
    final detected = autoDetectCompany(v);
    if (detected != 'OTHER') {
      setState(() => _company = detected);
    }
  }

  void _submit() {
    final mailNo = _mailNoCtrl.text.trim();
    if (mailNo.isEmpty) {
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('请输入运单号')));
      return;
    }
    Navigator.pop(context, {
      'code': _company,
      'mail_no': mailNo,
      'phone': _phoneCtrl.text.trim(),
    });
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding:
          EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(24, 20, 24, 32),
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
            const SizedBox(height: 20),
            Text('添加运单',
                style: TextStyle(
                    color: scheme.onSurface,
                    fontSize: 22,
                    fontWeight: FontWeight.w700)),
            const SizedBox(height: 20),
            TextField(
              controller: _mailNoCtrl,
              autofocus: true,
              onChanged: _onMailNoChanged,
              decoration: InputDecoration(
                labelText: '运单号',
                hintText: '请输入快递运单号',
                prefixIcon: const Icon(Icons.tag),
                filled: true,
                fillColor: scheme.surfaceContainerHighest,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide: BorderSide.none,
                ),
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _phoneCtrl,
              keyboardType: TextInputType.phone,
              decoration: InputDecoration(
                labelText: '手机尾号（选填，部分快递需要）',
                prefixIcon: const Icon(Icons.phone_iphone),
                filled: true,
                fillColor: scheme.surfaceContainerHighest,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(14),
                  borderSide: BorderSide.none,
                ),
              ),
            ),
            const SizedBox(height: 20),
            Text('快递公司',
                style: TextStyle(
                    color: scheme.onSurfaceVariant,
                    fontSize: 13,
                    fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: kCompanyCodes.map((code) {
                final selected = code == _company;
                return ChoiceChip(
                  label: Text(companyNameOf(code)),
                  selected: selected,
                  onSelected: (_) => setState(() => _company = code),
                  selectedColor: scheme.primaryContainer,
                  labelStyle: TextStyle(
                    color: selected
                        ? scheme.onPrimaryContainer
                        : scheme.onSurfaceVariant,
                    fontWeight: FontWeight.w600,
                  ),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12)),
                  side: BorderSide.none,
                );
              }).toList(),
            ),
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                onPressed: _submit,
                child: const Text('添加并查询'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
