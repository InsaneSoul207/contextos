using System;
using System.IO;
using System.Threading;
using System.Windows.Forms;

namespace ContextOSDesktop;

static class Program
{
    [STAThread]
    static void Main()
    {
        Application.SetUnhandledExceptionMode(UnhandledExceptionMode.CatchException);
        Application.ThreadException += (s, e) =>
        {
            File.WriteAllText("desktop_crash.log", "ThreadException: " + e.Exception.ToString());
        };
        AppDomain.CurrentDomain.UnhandledException += (s, e) =>
        {
            File.WriteAllText("desktop_crash.log", "UnhandledException: " + e.ExceptionObject?.ToString());
        };

        File.WriteAllText("desktop_run.log", "Starting at " + DateTime.Now);
        try
        {
            ApplicationConfiguration.Initialize();
            var form = new Form1();
            File.AppendAllText("desktop_run.log", "\nForm created successfully");
            Application.Run(form);
            File.AppendAllText("desktop_run.log", "\nApplication.Run ended cleanly");
        }
        catch (Exception ex)
        {
            File.WriteAllText("desktop_crash.log", "Main catch: " + ex.ToString());
        }
    }    
}
