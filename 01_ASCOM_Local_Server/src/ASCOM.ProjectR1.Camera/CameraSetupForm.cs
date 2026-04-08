using ASCOM.Utilities;
using System;
using System.Drawing;
using System.Windows.Forms;

namespace ASCOM.ProjectR1
{
    internal sealed class CameraSetupForm : Form
    {
        private readonly PythonApiClient _api;
        private ComboBox _readoutCombo;
        private ComboBox _gainCombo;
        private TextBox _profileIdBox;

        public CameraSetupForm(PythonApiClient api)
        {
            _api = api;
            Text = "GreatEyes 9.0 (Project_R1) — Properties";
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            MinimizeBox = false;
            StartPosition = FormStartPosition.CenterScreen;
            ClientSize = new Size(420, 220);

            var y = 12;
            Controls.Add(MkLabel("Readout speed (kHz):", 12, y));
            _readoutCombo = new ComboBox
            {
                DropDownStyle = ComboBoxStyle.DropDownList,
                Location = new Point(160, y - 2),
                Width = 240,
            };
            foreach (var label in Camera.ReadoutModeLabels)
                _readoutCombo.Items.Add(label);
            Controls.Add(_readoutCombo);
            y += 32;

            Controls.Add(MkLabel("Gain mode:", 12, y));
            _gainCombo = new ComboBox
            {
                DropDownStyle = ComboBoxStyle.DropDownList,
                Location = new Point(160, y - 2),
                Width = 240,
            };
            _gainCombo.Items.Add("High capacity (SDK 0)");
            _gainCombo.Items.Add("Low noise (SDK 1)");
            Controls.Add(_gainCombo);
            y += 32;

            Controls.Add(MkLabel("Profile ID (activate):", 12, y));
            _profileIdBox = new TextBox { Location = new Point(160, y - 2), Width = 240 };
            Controls.Add(_profileIdBox);
            y += 36;

            var activateBtn = new Button { Text = "Activate profile", Location = new Point(12, y), Width = 130 };
            activateBtn.Click += (_, __) => ActivateProfile();
            Controls.Add(activateBtn);

            var okBtn = new Button { Text = "OK", DialogResult = DialogResult.OK, Location = new Point(220, y), Width = 80 };
            var cancelBtn = new Button { Text = "Cancel", DialogResult = DialogResult.Cancel, Location = new Point(310, y), Width = 80 };
            Controls.Add(okBtn);
            Controls.Add(cancelBtn);
            AcceptButton = okBtn;
            CancelButton = cancelBtn;

            Load += (_, __) => LoadForm();
            okBtn.Click += (_, __) => SaveAndClose();
        }

        private static Label MkLabel(string text, int x, int y)
        {
            return new Label { Text = text, Location = new Point(x, y), AutoSize = true };
        }

        private void LoadForm()
        {
            try
            {
                using (var profile = new Profile())
                {
                    profile.DeviceType = "Camera";
                    var pid = profile.GetValue(Camera.DriverId, "ProfileId", string.Empty);
                    if (!string.IsNullOrWhiteSpace(pid))
                        _profileIdBox.Text = pid;
                }
            }
            catch
            {
            }

            try
            {
                var st = _api.GetJson("/settings");
                var speed = CameraApiValueReader.ReadInt(st, "readout_speed");
                var mode = CameraApiValueReader.ReadString(st, "default_gain_mode");
                var idx = Array.IndexOf(Camera.ReadoutSpeedKhz, speed);
                _readoutCombo.SelectedIndex = idx >= 0 ? idx : 0;
                _gainCombo.SelectedIndex = mode == "0" ? 0 : 1;
            }
            catch
            {
                _readoutCombo.SelectedIndex = 0;
                _gainCombo.SelectedIndex = 1;
            }
        }

        private void SaveAndClose()
        {
            try
            {
                using (var profile = new Profile())
                {
                    profile.DeviceType = "Camera";
                    profile.WriteValue(Camera.DriverId, "ProfileId", _profileIdBox.Text.Trim());
                }
            }
            catch
            {
            }

            if (_readoutCombo.SelectedIndex < 0 || _readoutCombo.SelectedIndex >= Camera.ReadoutSpeedKhz.Length)
                return;
            var speed = Camera.ReadoutSpeedKhz[_readoutCombo.SelectedIndex];
            var gain = _gainCombo.SelectedIndex == 0 ? "0" : "1";
            _api.PutJson("/settings", new
            {
                readout_speed = speed,
                default_gain_mode = gain,
            });
        }

        private void ActivateProfile()
        {
            var id = _profileIdBox.Text.Trim();
            if (string.IsNullOrEmpty(id))
            {
                MessageBox.Show(this, "Enter profile UUID first.", Text, MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }

            try
            {
                _api.PostJson("/camera/profiles/" + id + "/activate");
                MessageBox.Show(this, "Profile activated. Reconnect ASCOM if the camera was connected.", Text, MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
            catch (Exception ex)
            {
                MessageBox.Show(this, ex.Message, Text, MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
        }
    }
}
