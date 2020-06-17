import psutil
import time


def checkIfProcessRunning(process_name):
    for proc in psutil.process_iter():
        try:
            if process_name.lower() in proc.name().lower():
                print(proc.as_dict(attrs=['pid', 'name']))
                # proc.terminate()
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            print("ERROR!")
    return False

if __name__ == "__main__":
    while True:
        process = checkIfProcessRunning("Java")
        if process:
            process.terminate()
            time.sleep(2)
        else:
            print("Java is dead!")
            break

    print("All cleared.")


