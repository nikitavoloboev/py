import subprocess
import sys


def get_window_titles(app_name):
    # AppleScript command to get window titles
    applescript = f'''
    tell application "{app_name}"
        try
            set windowList to name of every window
            return windowList
        on error
            return "Error: Could not get window titles or no windows open for " & "{app_name}"
        end try
    end tell
    '''

    try:
        # Execute AppleScript and capture output
        result = subprocess.run(
            ["osascript", "-e", applescript], capture_output=True, text=True
        )

        if result.stderr:
            return f"Error: {result.stderr.strip()}"

        windows = result.stdout.strip()
        if windows.startswith("Error:"):
            return windows

        # Convert the comma-separated list to a Python list
        if windows:
            window_list = [w.strip() for w in windows.split(",")]
            return window_list
        else:
            return "No windows open"

    except Exception as e:
        return f"Error executing script: {str(e)}"


if __name__ == "__main__":
    # Check if app name is provided as command line argument
    if len(sys.argv) != 2:
        print("Usage: python script.py 'Application Name'")
        sys.exit(1)

    app_name = sys.argv[1]
    result = get_window_titles(app_name)

    # Print results
    if isinstance(result, list):
        print(f"Window titles for {app_name}:")
        for i, title in enumerate(result, 1):
            print(f"{i}. {title}")
    else:
        print(result)
