import logging
import subprocess
import time

from os import path
from uploader_utils.kill_java import checkIfProcessRunning


def get_logger():
    """Creating and setting a LOGGER"""
    logger = logging.getLogger(__name__)

    f_handler = logging.FileHandler(r"D:\Projects\Uploader\NATS_3.0\TCRunner\logs\group_run.log", mode="w")
    s_handler = logging.StreamHandler()
    logger.setLevel(logging.DEBUG)
    f_handler.setLevel(logging.DEBUG)
    s_handler.setLevel(logging.INFO)

    f_format = logging.Formatter(
        "%(asctime)s | %(name)s | %(funcName)-16s | %(levelname)-8s | %(message)s")
    s_format = logging.Formatter(
        "%(asctime)s - %(message)s"
    )
    f_handler.setFormatter(f_format)
    s_handler.setFormatter(s_format)

    logger.addHandler(f_handler)
    logger.addHandler(s_handler)
    """End of the LOGGER creation"""
    return logger


class GroupRun:
    NATS_DIR = "D:\\Projects\\Uploader\\NATS_3.0\\"
    RUN_FILE = path.join(NATS_DIR, "TCRunner", "run.cmd ")
    scripts_source = "D:\\Projects\\Uploader\\NATS_3.0\\_Tests_NGP\\Group.txt"
    scripts_list = []

    def __init__(self):
        self.logger = get_logger()
        self._get_scripts_list()

    def _get_scripts_list(self):
        try:
            with open(self.scripts_source) as file:
                for line in file:
                    self.scripts_list.append(line.rstrip())
        except IOError:
            self.logger.error("File not found")

    def clear_com_port(self):
        while True:
            process = checkIfProcessRunning("Java")
            if process:
                process.terminate()
                time.sleep(2)
            else:
                break
        self.logger.debug("COM port cleared")

    def _get_manifest(self, script):
        print(path.join(self.NATS_DIR, "_Tests_NGP", script, "manifest_770_1880.json"))
        if path.exists(path.join(self.NATS_DIR, "_Tests_NGP", script, "manifest_770_1880.json")):
            self.logger.info("Selected manifest_770_1880.json")
            return "manifest_770_1880.json"
        elif path.exists(path.join(self.NATS_DIR, "_Tests_NGP", script, "manifest_700_1800.json")):
            self.logger.info("Selected manifest_700_1800.json")
            return "manifest_700_1800.json"
        elif path.exists(path.join(self.NATS_DIR, "_Tests_NGP", script, "manifest_720_1809.json")):
            self.logger.info("Selected manifest_720_1809.json")
            return "manifest_720_1809.json"
        elif path.exists(path.join(self.NATS_DIR, "_Tests_NGP", script, "manifest_780_1884.json")):
            self.logger.info("Selected manifest_780_1884.json")
            return "manifest_780_1884.json"
        elif path.exists(path.join(self.NATS_DIR, "_Tests_NGP", script, "manifest.json")):
            self.logger.info("Selected manifest.json")
            return "manifest.json"
        else:
            raise IOError("File not found")

    def run_tc(self):
        try:
            for script in self.scripts_list:
                self.logger.debug("Clearing com port...")
                self.clear_com_port()

                self.logger.info(f"Starting {script}...")
                manifest = self._get_manifest(path.join(self.NATS_DIR, "_Tests_NGP", script))
                test_path = path.join(self.NATS_DIR, "_Tests_NGP", script, manifest)

                process = subprocess.call([self.RUN_FILE, test_path])

                if process != 0:
                    self.logger.error("Errors")
                else:
                    self.logger.info("OK")

                time.sleep(60)
            self.logger.info("Finished")
        except IOError:
            self.logger.error("File not found")
        except Exception as e:
            self.logger.error("other error %s", e)


if __name__ == "__main__":
    action = GroupRun()

    action.run_tc()
