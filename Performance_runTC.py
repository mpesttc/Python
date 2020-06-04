import argparse
import csv
import glob
import logging
import os.path
import re
import shutil
import subprocess
import time
import zipfile

from configs.config import Config

from datetime import datetime


def get_parser():
    """Define a parser"""
    parser = argparse.ArgumentParser(description="Run JS scripts")

    # Script name
    parser.add_argument("--script",
                        action="store",
                        dest="script_name",
                        required=True,
                        help="JS script to run")
    # Run times
    parser.add_argument("--run_times",
                        type=int,
                        action="store",
                        dest="run_times",
                        default=1,
                        help="Number of runs")

    run_args = parser.parse_args()
    return run_args


def get_logger():
    """Creating and setting a LOGGER"""
    logger = logging.getLogger(__name__)

    f_handler = logging.FileHandler("startLog.log", mode="w")
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


def check_text_decorator(func):
    """Checks if log's text is not None"""
    def wrapper(self):
        if not self.full_text:
            logger.error("File is empty")
            return
        return func(self)

    return wrapper


class CLIUploaderParser:
    pattern_time = r"\d{4}[-\d\d]+\s[:?\d{2}]*"
    pattern_version = r"serialNumber for upload: (\d.\d)"
    pattern_user = r"username=((.+?)\])"

    time_format_data = "%Y-%m-%d %H:%M:%S"

    def __init__(self, temp_dir, logs_dir=None):
        if not logs_dir:
            logger.debug("looking for logs")
            logs_dir = Config().run_folder

        self.logs_dir = logs_dir
        self.temp_dir = temp_dir
        self.last_log = self._get_last_log()
        self._make_log_copy()
        self.log_file = os.path.join(self.temp_dir, os.path.basename(self.last_log))
        self.full_text = self._get_log_content()

    def _get_last_log(self):
        """Find and return last created log in the logs folder"""
        logger.debug(f"logs_dir = {self.logs_dir}")
        files_list = list(glob.iglob(os.path.join(self.logs_dir, "*.log")))
        if not files_list:
            logger.error("Logs not found")
            return
        last_log = max(files_list, key=os.path.getctime)
        logger.debug(f"Selected log file: {os.path.basename(last_log)}")

        return last_log

    def _get_log_content(self):
        """Read and return all the text rows from a log file"""
        if not self.log_file:
            logger.error("File not found")
            return
        with open(self.log_file) as fs:
            full_text = fs.readlines()
        if not full_text:
            logger.error("File is empty")
            return
        else:
            logger.info("File reading - DONE")
            return full_text

    @check_text_decorator
    def get_upload_time(self):
        """Looks for the start time and the end time of the upload and returns them"""
        first_line = re.search(self.pattern_time, self.full_text[0])
        last_line = re.search(self.pattern_time, self.full_text[-1])
        if not first_line or not last_line:
            logger.error("Matches not found")
            return

        start_time = datetime.strptime(first_line.group(), self.time_format_data)
        end_time = datetime.strptime(last_line.group(), self.time_format_data)
        logger.debug(start_time)
        logger.debug(end_time)
        logger.info("Reading time - DONE")

        return start_time, end_time

    @check_text_decorator
    def get_cli_version(self):
        """Gets CLI uploader version"""
        for row in self.full_text:
            search_ver = re.search(self.pattern_version, row)
            if search_ver:
                version = search_ver.group(1)
                logger.info(f"CLI version: {version}")
                return version
        logger.error("Version not found.")
        return "Not found"

    @check_text_decorator
    def get_user(self):
        """Gets uploader user"""
        for row in self.full_text:
            search_user = re.search(self.pattern_user, row)
            if search_user:
                logger.info(f"User: {search_user.group(2)}")
                return search_user.group(2)
        logger.error("User not found")
        return "User not found"

    def _make_log_copy(self):
        """Copies found last log to the temp folder"""
        try:
            if not os.path.exists(self.temp_dir):
                os.mkdir(self.temp_dir)
                logger.info(f"Folder {self.temp_dir} has been created")
            shutil.copy(self.last_log, self.temp_dir)
            logger.info(f"Log file has been copied to the {self.temp_dir} folder")
        except OSError:
            logger.exception("System could not create specific folder or copy file")

    def data_collect(self, step, data, test_script):
        """Saves data from each log file for analyzing"""
        upload_time = self.get_upload_time()
        if not upload_time:
            start_time, end_time = 0, 0  # sets default parameter
        else:
            start_time, end_time = upload_time
        data.append({"№": f"{step + 1}",
                     "Uploader ver": f"{self.get_cli_version()}",
                     "User": f"{self.get_user()}",
                     "Script": f"{test_script}",
                     "Start": f"{start_time}",
                     "End": f"{end_time}",
                     "Duration": f"{end_time - start_time}"})
        return data


class PerformanceRun:
    """Class allows run JavaScript test via NATS"""
    NATS_DIR = Config().nats_dir
    RUN_FILE = os.path.join(NATS_DIR, "TCRunner", "run.cmd ")

    data = []

    def __init__(self, script_name, temp_dir=".\\Temp\\"):
        self.TEST_NAME_JS = script_name
        self.temp_dir = temp_dir

    def get_script_to_run(self):
        """Chose a correct manifest in the test case"""
        script_location = os.path.join(
            self.NATS_DIR, "_Tests_NGP", self.TEST_NAME_JS
        )

        script_js = os.path.join(
            script_location, "manifest.json"
        )
        script_js_1880 = os.path.join(
            script_location, "manifest_770_1880.json"
        )
        script_js_1884 = os.path.join(
            script_location, "manifest_780_1884.json"
        )

        if os.path.isfile(script_js_1880):
            return script_js_1880
        elif os.path.isfile(script_js):
            return script_js
        elif os.path.isfile(script_js_1884):
            return script_js_1884
        else:
            logger.exception("File not found!")

    def save_to_csv(self, file_name="Results.csv"):
        """Save data to .csv file"""
        try:
            with open(os.path.join(self.temp_dir, file_name),  mode="w", newline="") as file:
                fields = self.data[0].keys()
                writer = csv.DictWriter(file, fieldnames=fields)

                writer.writeheader()
                writer.writerows(self.data)
            logger.info(f"Data has been added to {file_name}")
        except OSError:
            logger.exception("There are some problems with file")

    def zip_logs(self, uploader_version):
        """Archiving log and scv files and delete after that"""
        try:
            name = f"Performance_{self.TEST_NAME_JS}_{uploader_version}.zip"
            with zipfile.ZipFile(os.path.join(self.temp_dir, name), "w") as zip_file:
                for file in glob.glob(os.path.join(self.temp_dir, "*.*")):
                    if file.endswith(".log") or file.endswith(".csv"):
                        file_name = str(os.path.basename(file))
                        zip_file.write(file, file_name)
                        logger.info(f"File {file_name} has been archived")
                        os.remove(file)
            logger.info("Archiving - DONE")
        except OSError:
            logger.exception("No access to file")

    def run_tc(self, run_times):
        """Run script via NATS"""
        try:
            script_to_run = self.get_script_to_run()
            logger.info(f"Starting new script {self.TEST_NAME_JS}...  for {run_times} times")
            for step in range(run_times):

                process = subprocess.call([self.RUN_FILE, script_to_run])

                logger.debug(f"Process = {process}")
                if process != 0:
                    logger.error("Process ended with errors!!!")
                    break

                logger.info("Process finished with status SUCCESSFUL")
                logger.info("Parsing logs...")

                log_parser = CLIUploaderParser(self.temp_dir)

                log_parser.data_collect(step, self.data, self.TEST_NAME_JS)

                logger.info("Duration = %s", self.data[-1].get("Duration"))

                if step != (run_times - 1):
                    logger.info("Waiting 10 sec...")
                    time.sleep(10)

            logger.info("Saving results...")
            self.save_to_csv()

            logger.info("Archiving...")
            self.zip_logs(self.data[-1].get("Uploader ver"))

            logger.info("DONE!")

        except OSError as err:
            logger.error(f"OS error: {0}".format(err), exc_info=True)
        except Exception as e:
            logger.error("other error %s", e)


if __name__ == "__main__":
    args = get_parser()
    logger = get_logger()
    # _BLE_Uploader_Smoke_Test_770
    # _BLE_AHCL_Uploader_Smoke

    PerformanceRun(args.script_name).run_tc(args.run_times)
