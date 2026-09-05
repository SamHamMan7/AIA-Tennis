using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;

internal static class Program
{
    private const string MarkerName = ".aia-local-bots";

    [STAThread]
    private static void Main()
    {
        try
        {
            string baseDir = AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar);
            string gameExe = Path.Combine(baseDir, "Aialanders.exe");
            string botsDir = Path.Combine(baseDir, "Bots");

            Directory.CreateDirectory(botsDir);

            if (!File.Exists(gameExe))
            {
                MessageBox.Show(
                    "Put AIA-Tennis.exe in the same folder as Aialanders.exe, then run it again.",
                    "AIA-Tennis",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Information);
                OpenFolder(botsDir);
                return;
            }

            string profile = Environment.GetEnvironmentVariable("USERPROFILE");
            if (string.IsNullOrWhiteSpace(profile))
                profile = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);

            string savesParent = Path.Combine(
                profile,
                "AppData",
                "LocalLow",
                "Unicorn One",
                "AIComp",
                "Saves");

            string tennisSaveDir = Path.Combine(savesParent, "Tennis");
            Directory.CreateDirectory(savesParent);

            bool directLocalMode = TryMapTennisFolderToBots(tennisSaveDir, botsDir);

            if (!directLocalMode)
            {
                Directory.CreateDirectory(tennisSaveDir);
                CopyTxtFiles(botsDir, tennisSaveDir, true);
            }

            string[] bots = Directory.GetFiles(botsDir, "*.txt", SearchOption.TopDirectoryOnly);
            if (bots.Length == 0)
            {
                MessageBox.Show(
                    "The local Bots folder is ready. Put DeepCourt.txt (or any Tennis bot .txt file) into Bots, then launch AIA-Tennis.exe again.",
                    "AIA-Tennis",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Information);
                OpenFolder(botsDir);
                return;
            }

            ProcessStartInfo psi = new ProcessStartInfo();
            psi.FileName = gameExe;
            psi.WorkingDirectory = baseDir;
            psi.UseShellExecute = true;

            Process game = Process.Start(psi);

            // If junction creation was unavailable, keep the same simple user
            // experience by syncing game-written .txt files back after exit.
            if (!directLocalMode && game != null)
            {
                try
                {
                    game.WaitForExit();
                    CopyTxtFiles(tennisSaveDir, botsDir, true);
                }
                catch
                {
                    // The game has already launched successfully; a failed
                    // post-exit sync should not turn that into a launch error.
                }
            }
        }
        catch (Exception ex)
        {
            MessageBox.Show(
                "AIA-Tennis could not prepare the local Bots folder.\n\n" + ex.Message,
                "AIA-Tennis",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error);
        }
    }

    private static bool TryMapTennisFolderToBots(string tennisSaveDir, string botsDir)
    {
        string markerInSave = Path.Combine(tennisSaveDir, MarkerName);

        // If our marker is visible through Tennis, the existing mapping already
        // points at the local Bots directory. Nothing else needs to be done.
        if (Directory.Exists(tennisSaveDir) && File.Exists(markerInSave))
            return true;

        string backup = null;

        if (Directory.Exists(tennisSaveDir))
        {
            FileAttributes attrs = File.GetAttributes(tennisSaveDir);

            // Do not destroy an unknown reparse point. Fall back to transparent
            // pre/post launch sync instead.
            if ((attrs & FileAttributes.ReparsePoint) != 0)
                return false;

            // Preserve any existing Tennis saves before replacing the physical
            // directory with a junction. Also migrate missing .txt files locally.
            CopyTxtFiles(tennisSaveDir, botsDir, false);

            backup = tennisSaveDir + ".backup-" + DateTime.Now.ToString("yyyyMMdd-HHmmss");
            Directory.Move(tennisSaveDir, backup);
        }

        try
        {
            File.WriteAllText(Path.Combine(botsDir, MarkerName), "AIA-Tennis local bot directory mapping.\r\n");

            ProcessStartInfo mklink = new ProcessStartInfo();
            mklink.FileName = "cmd.exe";
            mklink.Arguments = "/c mklink /J \"" + tennisSaveDir + "\" \"" + botsDir + "\"";
            mklink.UseShellExecute = false;
            mklink.CreateNoWindow = true;
            mklink.RedirectStandardOutput = true;
            mklink.RedirectStandardError = true;

            using (Process p = Process.Start(mklink))
            {
                p.WaitForExit();
                if (p.ExitCode == 0 && Directory.Exists(tennisSaveDir) && File.Exists(markerInSave))
                    return true;
            }
        }
        catch
        {
            // Fall through to restore/fallback mode.
        }

        // Junction setup failed. Restore the original directory if one existed,
        // otherwise create a normal save directory for sync mode.
        try
        {
            if (Directory.Exists(tennisSaveDir))
            {
                FileAttributes attrs = File.GetAttributes(tennisSaveDir);
                if ((attrs & FileAttributes.ReparsePoint) != 0)
                    Directory.Delete(tennisSaveDir);
            }

            if (!Directory.Exists(tennisSaveDir))
            {
                if (!string.IsNullOrEmpty(backup) && Directory.Exists(backup))
                    Directory.Move(backup, tennisSaveDir);
                else
                    Directory.CreateDirectory(tennisSaveDir);
            }
        }
        catch
        {
            // The caller can surface the actual filesystem failure if sync fails.
        }

        return false;
    }

    private static void CopyTxtFiles(string source, string destination, bool overwrite)
    {
        if (!Directory.Exists(source))
            return;

        Directory.CreateDirectory(destination);

        foreach (string file in Directory.GetFiles(source, "*.txt", SearchOption.TopDirectoryOnly))
        {
            string dest = Path.Combine(destination, Path.GetFileName(file));
            if (!File.Exists(dest) || overwrite)
                File.Copy(file, dest, overwrite);
        }
    }

    private static void OpenFolder(string folder)
    {
        try
        {
            ProcessStartInfo psi = new ProcessStartInfo();
            psi.FileName = "explorer.exe";
            psi.Arguments = "\"" + folder + "\"";
            psi.UseShellExecute = true;
            Process.Start(psi);
        }
        catch
        {
        }
    }
}
