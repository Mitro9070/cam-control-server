
namespace ASCOM.MyFunkyCamera
{
    partial class SetupDialogForm
    {
        /// <summary>
        /// Required designer variable.
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        /// Clean up any resources being used.
        /// </summary>
        /// <param name="disposing">true if managed resources should be disposed; otherwise, false.</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows Form Designer generated code

        /// <summary>
        /// Required method for Designer support - do not modify
        /// the contents of this method with the code editor.
        /// </summary>
        private void InitializeComponent()
        {
            System.Windows.Forms.Label labelSpeed;
            System.Windows.Forms.Label labelShutter;
            this.cmdOK = new System.Windows.Forms.Button();
            this.cmdCancel = new System.Windows.Forms.Button();
            this.label1 = new System.Windows.Forms.Label();
            this.picASCOM = new System.Windows.Forms.PictureBox();
            this.labelGain = new System.Windows.Forms.Label();
            this.labelCooler = new System.Windows.Forms.Label();
            this.textBoxCooler = new System.Windows.Forms.TextBox();
            this.chkTrace = new System.Windows.Forms.CheckBox();
            this.comboBoxSpeed = new System.Windows.Forms.ComboBox();
            this.comboBoxGain = new System.Windows.Forms.ComboBox();
            this.comboBoxShutter = new System.Windows.Forms.ComboBox();
            labelSpeed = new System.Windows.Forms.Label();
            labelShutter = new System.Windows.Forms.Label();
            ((System.ComponentModel.ISupportInitialize)(this.picASCOM)).BeginInit();
            this.SuspendLayout();
            // 
            // labelSpeed
            // 
            labelSpeed.AutoSize = true;
            labelSpeed.Location = new System.Drawing.Point(12, 207);
            labelSpeed.Name = "labelSpeed";
            labelSpeed.Size = new System.Drawing.Size(105, 13);
            labelSpeed.TabIndex = 14;
            labelSpeed.Text = "Readout speed, kHz";
            labelSpeed.Click += new System.EventHandler(this.coolerLevel_Click_1);
            // 
            // labelShutter
            // 
            labelShutter.AutoSize = true;
            labelShutter.Location = new System.Drawing.Point(12, 252);
            labelShutter.Name = "labelShutter";
            labelShutter.Size = new System.Drawing.Size(67, 13);
            labelShutter.TabIndex = 20;
            labelShutter.Text = "Shutter state";
            labelShutter.Click += new System.EventHandler(this.label2_Click);
            // 
            // cmdOK
            // 
            this.cmdOK.Anchor = ((System.Windows.Forms.AnchorStyles)((System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right)));
            this.cmdOK.DialogResult = System.Windows.Forms.DialogResult.OK;
            this.cmdOK.Location = new System.Drawing.Point(106, 299);
            this.cmdOK.Name = "cmdOK";
            this.cmdOK.Size = new System.Drawing.Size(59, 24);
            this.cmdOK.TabIndex = 0;
            this.cmdOK.Text = "OK";
            this.cmdOK.UseVisualStyleBackColor = true;
            this.cmdOK.Click += new System.EventHandler(this.cmdOK_Click);
            // 
            // cmdCancel
            // 
            this.cmdCancel.Anchor = ((System.Windows.Forms.AnchorStyles)((System.Windows.Forms.AnchorStyles.Bottom | System.Windows.Forms.AnchorStyles.Right)));
            this.cmdCancel.DialogResult = System.Windows.Forms.DialogResult.Cancel;
            this.cmdCancel.Location = new System.Drawing.Point(196, 298);
            this.cmdCancel.Name = "cmdCancel";
            this.cmdCancel.Size = new System.Drawing.Size(59, 25);
            this.cmdCancel.TabIndex = 1;
            this.cmdCancel.Text = "Cancel";
            this.cmdCancel.UseVisualStyleBackColor = true;
            this.cmdCancel.Click += new System.EventHandler(this.cmdCancel_Click);
            // 
            // label1
            // 
            this.label1.Font = new System.Drawing.Font("Microsoft Sans Serif", 8.25F, System.Drawing.FontStyle.Bold, System.Drawing.GraphicsUnit.Point, ((byte)(204)));
            this.label1.Location = new System.Drawing.Point(12, 9);
            this.label1.Name = "label1";
            this.label1.Size = new System.Drawing.Size(153, 25);
            this.label1.TabIndex = 2;
            this.label1.Text = "CCD parameters\r\n";
            this.label1.TextAlign = System.Drawing.ContentAlignment.MiddleCenter;
            this.label1.Click += new System.EventHandler(this.label1_Click);
            // 
            // picASCOM
            // 
            this.picASCOM.Anchor = ((System.Windows.Forms.AnchorStyles)((System.Windows.Forms.AnchorStyles.Top | System.Windows.Forms.AnchorStyles.Right)));
            this.picASCOM.Cursor = System.Windows.Forms.Cursors.Hand;
            this.picASCOM.Image = global::ASCOM.MyFunkyCamera.Properties.Resources.ASCOM;
            this.picASCOM.Location = new System.Drawing.Point(207, 9);
            this.picASCOM.Name = "picASCOM";
            this.picASCOM.Size = new System.Drawing.Size(48, 56);
            this.picASCOM.SizeMode = System.Windows.Forms.PictureBoxSizeMode.AutoSize;
            this.picASCOM.TabIndex = 3;
            this.picASCOM.TabStop = false;
            this.picASCOM.Click += new System.EventHandler(this.BrowseToAscom);
            this.picASCOM.DoubleClick += new System.EventHandler(this.BrowseToAscom);
            // 
            // labelGain
            // 
            this.labelGain.AutoSize = true;
            this.labelGain.Location = new System.Drawing.Point(12, 113);
            this.labelGain.Name = "labelGain";
            this.labelGain.Size = new System.Drawing.Size(72, 13);
            this.labelGain.TabIndex = 8;
            this.labelGain.Text = "Gain, e-/ADU";
            this.labelGain.Click += new System.EventHandler(this.label3_Click);
            // 
            // labelCooler
            // 
            this.labelCooler.AutoSize = true;
            this.labelCooler.Location = new System.Drawing.Point(12, 161);
            this.labelCooler.Name = "labelCooler";
            this.labelCooler.Size = new System.Drawing.Size(95, 13);
            this.labelCooler.TabIndex = 16;
            this.labelCooler.Text = "Cooler level [0..25]";
            this.labelCooler.Click += new System.EventHandler(this.label3_Click_1);
            // 
            // textBoxCooler
            // 
            this.textBoxCooler.DataBindings.Add(new System.Windows.Forms.Binding("Text", global::ASCOM.MyFunkyCamera.Properties.Settings.Default, "CoolerLevel", true, System.Windows.Forms.DataSourceUpdateMode.OnPropertyChanged));
            this.textBoxCooler.Location = new System.Drawing.Point(140, 158);
            this.textBoxCooler.Name = "textBoxCooler";
            this.textBoxCooler.Size = new System.Drawing.Size(88, 20);
            this.textBoxCooler.TabIndex = 17;
            this.textBoxCooler.Text = global::ASCOM.MyFunkyCamera.Properties.Settings.Default.CoolerLevel;
            this.textBoxCooler.TextChanged += new System.EventHandler(this.textBoxCooler_TextChanged);
            // 
            // chkTrace
            // 
            this.chkTrace.AutoSize = true;
            this.chkTrace.Checked = global::ASCOM.MyFunkyCamera.Properties.Settings.Default.TraceEnabled;
            this.chkTrace.CheckState = System.Windows.Forms.CheckState.Checked;
            this.chkTrace.DataBindings.Add(new System.Windows.Forms.Binding("Checked", global::ASCOM.MyFunkyCamera.Properties.Settings.Default, "TraceEnabled", true, System.Windows.Forms.DataSourceUpdateMode.OnPropertyChanged));
            this.chkTrace.Location = new System.Drawing.Point(15, 303);
            this.chkTrace.Name = "chkTrace";
            this.chkTrace.Size = new System.Drawing.Size(69, 17);
            this.chkTrace.TabIndex = 6;
            this.chkTrace.Text = "Trace on";
            this.chkTrace.UseVisualStyleBackColor = true;
            // 
            // comboBoxSpeed
            // 
            this.comboBoxSpeed.DataBindings.Add(new System.Windows.Forms.Binding("Text", global::ASCOM.MyFunkyCamera.Properties.Settings.Default, "ReadoutSpeed", true, System.Windows.Forms.DataSourceUpdateMode.OnPropertyChanged));
            this.comboBoxSpeed.FormattingEnabled = true;
            this.comboBoxSpeed.Items.AddRange(new object[] {
            "500",
            "1000",
            "2800"});
            this.comboBoxSpeed.Location = new System.Drawing.Point(140, 204);
            this.comboBoxSpeed.Name = "comboBoxSpeed";
            this.comboBoxSpeed.Size = new System.Drawing.Size(88, 21);
            this.comboBoxSpeed.TabIndex = 18;
            this.comboBoxSpeed.Text = global::ASCOM.MyFunkyCamera.Properties.Settings.Default.ReadoutSpeed;
            this.comboBoxSpeed.SelectedIndexChanged += new System.EventHandler(this.comboBoxSpeed_SelectedIndexChanged);
            // 
            // comboBoxGain
            // 
            this.comboBoxGain.DataBindings.Add(new System.Windows.Forms.Binding("Text", global::ASCOM.MyFunkyCamera.Properties.Settings.Default, "GainName", true, System.Windows.Forms.DataSourceUpdateMode.OnPropertyChanged));
            this.comboBoxGain.FormattingEnabled = true;
            this.comboBoxGain.Items.AddRange(new object[] {
            "1",
            "2"});
            this.comboBoxGain.Location = new System.Drawing.Point(140, 110);
            this.comboBoxGain.Name = "comboBoxGain";
            this.comboBoxGain.Size = new System.Drawing.Size(88, 21);
            this.comboBoxGain.TabIndex = 19;
            this.comboBoxGain.Text = global::ASCOM.MyFunkyCamera.Properties.Settings.Default.GainName;
            this.comboBoxGain.SelectedIndexChanged += new System.EventHandler(this.comboBoxGain_SelectedIndexChanged);
            // 
            // comboBoxShutter
            // 
            this.comboBoxShutter.DataBindings.Add(new System.Windows.Forms.Binding("Text", global::ASCOM.MyFunkyCamera.Properties.Settings.Default, "ShutterState", true, System.Windows.Forms.DataSourceUpdateMode.OnPropertyChanged));
            this.comboBoxShutter.FormattingEnabled = true;
            this.comboBoxShutter.Items.AddRange(new object[] {
            "0",
            "1",
            "2"});
            this.comboBoxShutter.Location = new System.Drawing.Point(140, 249);
            this.comboBoxShutter.Name = "comboBoxShutter";
            this.comboBoxShutter.Size = new System.Drawing.Size(88, 21);
            this.comboBoxShutter.TabIndex = 21;
            this.comboBoxShutter.Text = global::ASCOM.MyFunkyCamera.Properties.Settings.Default.ShutterState;
            // 
            // SetupDialogForm
            // 
            this.AutoScaleDimensions = new System.Drawing.SizeF(6F, 13F);
            this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;
            this.ClientSize = new System.Drawing.Size(290, 351);
            this.Controls.Add(this.comboBoxShutter);
            this.Controls.Add(labelShutter);
            this.Controls.Add(this.comboBoxGain);
            this.Controls.Add(this.comboBoxSpeed);
            this.Controls.Add(this.textBoxCooler);
            this.Controls.Add(this.labelCooler);
            this.Controls.Add(labelSpeed);
            this.Controls.Add(this.labelGain);
            this.Controls.Add(this.chkTrace);
            this.Controls.Add(this.picASCOM);
            this.Controls.Add(this.label1);
            this.Controls.Add(this.cmdCancel);
            this.Controls.Add(this.cmdOK);
            this.FormBorderStyle = System.Windows.Forms.FormBorderStyle.FixedDialog;
            this.MaximizeBox = false;
            this.MinimizeBox = false;
            this.Name = "SetupDialogForm";
            this.SizeGripStyle = System.Windows.Forms.SizeGripStyle.Hide;
            this.StartPosition = System.Windows.Forms.FormStartPosition.CenterScreen;
            this.Text = "MyFunkyCamera Setup";
            this.Load += new System.EventHandler(this.SetupDialogForm_Load);
            ((System.ComponentModel.ISupportInitialize)(this.picASCOM)).EndInit();
            this.ResumeLayout(false);
            this.PerformLayout();

        }

        #endregion

        private System.Windows.Forms.Button cmdOK;
        private System.Windows.Forms.Button cmdCancel;
        private System.Windows.Forms.Label label1;
        private System.Windows.Forms.PictureBox picASCOM;
        private System.Windows.Forms.CheckBox chkTrace;
        private System.Windows.Forms.Label labelGain;
        private System.Windows.Forms.Label labelCooler;
        private System.Windows.Forms.TextBox textBoxCooler;
        private System.Windows.Forms.ComboBox comboBoxSpeed;
        private System.Windows.Forms.ComboBox comboBoxGain;
        private System.Windows.Forms.ComboBox comboBoxShutter;
    }
}