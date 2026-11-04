using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Net.Http;
using System.Runtime.InteropServices;
using System.Threading.Tasks;
using System.Windows.Forms;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

namespace ContextOSDesktop;

public partial class Form1 : Form
{
    private WebView2 webView;
    private Process? backendProcess;
    private NotifyIcon trayIcon;
    private static readonly HttpClient httpClient = new() { Timeout = TimeSpan.FromSeconds(2) };

    // Win32 Global Hotkey Constants
    private const int WM_HOTKEY = 0x0312;
    private const uint MOD_ALT = 0x0001;
    private const uint MOD_CONTROL = 0x0002;
    private const uint MOD_SHIFT = 0x0004;
    private const uint MOD_NOREPEAT = 0x4000;
    private const uint VK_SPACE = 0x20;
    private const uint VK_K = 0x4B;

    private const int HOTKEY_CTRL_SPACE = 9001;
    private const int HOTKEY_CTRL_SHIFT_SPACE = 9002;
    private const int HOTKEY_ALT_SPACE = 9003;

    [DllImport("user32.dll")]
    private static extern bool RegisterHotKey(IntPtr hWnd, int id, uint fsModifiers, uint vk);

    [DllImport("user32.dll")]
    private static extern bool UnregisterHotKey(IntPtr hWnd, int id);

    [DllImport("user32.dll")]
    private static extern bool SetForegroundWindow(IntPtr hWnd);

    public Form1()
    {
        InitializeComponent();

        Text = "ContextOS — Personal AI Memory Infrastructure";
        StartPosition = FormStartPosition.CenterScreen;
        Size = new Size(1320, 860);
        MinimumSize = new Size(1000, 650);
        BackColor = Color.FromArgb(250, 248, 245);

        Icon appIcon = null;
        if (File.Exists("icon.ico"))
        {
            try { appIcon = new Icon("icon.ico"); Icon = appIcon; } catch { }
        }

        // System Tray Icon
        trayIcon = new NotifyIcon
        {
            Text = "ContextOS (Ctrl+Space to Recall)",
            Icon = appIcon ?? SystemIcons.Application,
            Visible = true
        };

        var trayMenu = new ContextMenuStrip();
        trayMenu.Items.Add("Open Spotlight (Ctrl+Space)", null, (s, e) => TriggerSpotlight());
        trayMenu.Items.Add("Open ContextOS Window", null, (s, e) => RestoreWindow());
        trayMenu.Items.Add("-");
        trayMenu.Items.Add("Exit ContextOS", null, (s, e) => Application.Exit());
        trayIcon.ContextMenuStrip = trayMenu;
        trayIcon.DoubleClick += (s, e) => RestoreWindow();

        webView = new WebView2
        {
            Dock = DockStyle.Fill,
            DefaultBackgroundColor = Color.FromArgb(250, 248, 245)
        };
        Controls.Add(webView);

        Load += Form1_Load;
        FormClosing += Form1_FormClosing;
    }

    private async void Form1_Load(object? sender, EventArgs e)
    {
        // Register OS-wide global shortcuts so they work across VS Code, Chrome, etc.
        try
        {
            RegisterHotKey(Handle, HOTKEY_CTRL_SPACE, MOD_CONTROL | MOD_NOREPEAT, VK_SPACE);
            RegisterHotKey(Handle, HOTKEY_CTRL_SHIFT_SPACE, MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, VK_SPACE);
            RegisterHotKey(Handle, HOTKEY_ALT_SPACE, MOD_ALT | MOD_NOREPEAT, VK_SPACE);
        }
        catch { }

        await EnsureBackendRunningAsync();

        try
        {
            await webView.EnsureCoreWebView2Async(null);
            webView.CoreWebView2.Settings.IsStatusBarEnabled = false;
            webView.CoreWebView2.Settings.AreDevToolsEnabled = true;

            // Listen for messages from frontend to minimize on Esc
            webView.CoreWebView2.WebMessageReceived += (s, args) =>
            {
                try
                {
                    string msg = args.TryGetWebMessageAsString();
                    if (msg == "spotlight-closed")
                    {
                        // Optionally keep in background
                    }
                }
                catch { }
            };

            webView.Source = new Uri("http://127.0.0.1:1420");
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                $"Could not initialize WebView2.\nPlease verify Microsoft Edge WebView2 Runtime is installed.\nError: {ex.Message}",
                "ContextOS",
                MessageBoxButtons.OK,
                MessageBoxIcon.Warning
            );
        }
    }

    protected override void WndProc(ref Message m)
    {
        if (m.Msg == WM_HOTKEY)
        {
            TriggerSpotlight();
        }
        base.WndProc(ref m);
    }

    private void RestoreWindow()
    {
        if (WindowState == FormWindowState.Minimized)
        {
            WindowState = FormWindowState.Normal;
        }
        Show();
        BringToFront();
        Activate();
        SetForegroundWindow(Handle);
    }

    private void TriggerSpotlight()
    {
        RestoreWindow();

        // Dispatch open-spotlight event directly into WebView2
        if (webView != null && webView.CoreWebView2 != null)
        {
            webView.CoreWebView2.ExecuteScriptAsync(
                "window.dispatchEvent(new CustomEvent('open-spotlight'));"
            );
        }
    }

    private async Task EnsureBackendRunningAsync()
    {
        bool isBackendRunning = false;
        try
        {
            var res = await httpClient.GetAsync("http://127.0.0.1:44480/health");
            isBackendRunning = res.IsSuccessStatusCode;
        }
        catch
        {
            isBackendRunning = false;
        }

        if (isBackendRunning) return;

        // Try to locate backend directory
        string baseDir = AppDomain.CurrentDomain.BaseDirectory;
        string projectDir = Path.GetFullPath(Path.Combine(baseDir, "..", "..", "..", ".."));
        string backendDir = Path.Combine(projectDir, "backend");

        if (!Directory.Exists(backendDir))
        {
            backendDir = @"C:\Users\Eshaan Mishra\OneDrive\Desktop\Sem-5\IMD\Project\contextos\backend";
        }

        if (Directory.Exists(backendDir))
        {
            try
            {
                var psi = new ProcessStartInfo
                {
                    FileName = "python",
                    Arguments = "-m uvicorn app.main:app --host 127.0.0.1 --port 44480",
                    WorkingDirectory = backendDir,
                    CreateNoWindow = true,
                    UseShellExecute = false,
                    WindowStyle = ProcessWindowStyle.Hidden
                };
                backendProcess = Process.Start(psi);
                await Task.Delay(1500);
            }
            catch { }
        }
    }

    private void Form1_FormClosing(object? sender, FormClosingEventArgs e)
    {
        // Unregister global hotkeys
        try
        {
            UnregisterHotKey(Handle, HOTKEY_CTRL_SPACE);
            UnregisterHotKey(Handle, HOTKEY_CTRL_SHIFT_SPACE);
            UnregisterHotKey(Handle, HOTKEY_ALT_SPACE);
        }
        catch { }

        // Clean up tray icon
        if (trayIcon != null)
        {
            trayIcon.Visible = false;
            trayIcon.Dispose();
        }

        try
        {
            if (backendProcess != null && !backendProcess.HasExited)
            {
                backendProcess.Kill(true);
            }
        }
        catch { }
    }
}
