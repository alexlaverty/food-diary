import os
from datetime import datetime, timedelta
from pathlib import Path
import requests
from jinja2 import Environment, FileSystemLoader
import os

class DataExtractor:
    def __init__(self, x_token: str, number_of_days: int, json_file: str, image_folder: str):
        self.x_token = x_token
        self.number_of_days = number_of_days
        self.json_file = json_file
        self.image_folder = image_folder

    def calculate_date_range(self):
        end_date = datetime.today()
        start_date = end_date - timedelta(days=self.number_of_days)
        return end_date, start_date

    def retrieve_image_id(self, entry):
        if entry["type"] == "food":
            for mealItem in entry["mealItems"]:
                if mealItem["hasImage"]:
                    img_id = mealItem["realmIdString"]
                    img_file_path = Path(self.image_folder, f"{img_id}.jpg")
                    if not self.check_file_exists(img_file_path):
                        self.download_image(img_id)

    def check_file_exists(self, file_path: Path) -> bool:
        if file_path.exists():
            print(f"The file '{file_path}' exists.")
            return True
        else:
            print(f"The file '{file_path}' does not exist.")
            return False

    def download_image(self, img_id: str) -> bool:
        food_img_file = Path(self.image_folder, f"{img_id}.jpg")
        print(f"Attempting image download: {img_id}")
        img_url_path = f"https://web.gohidoc.com/api/dashboard/me/images/{img_id}/"
        img_request = requests.get(img_url_path, headers={"x-token": self.x_token})
        if img_request.status_code == 200:
            img_data = img_request.content
            with open(food_img_file, 'wb') as handler:
                handler.write(img_data)
            return True
        else:
            img_txt = Path(self.image_folder, f"{img_id}.txt")
            with open(img_txt, "w") as file:
                file.write("No image downloaded")
            return False

    def get_cara_entries(self, start_date_str: str, end_date_str: str, entry_limit: str, offset: str):
        url = f"https://web.gohidoc.com/api/dashboard/me/data-points/?start={start_date_str}&end={end_date_str}&limit={entry_limit}&offset={offset}"
        print(url)
        r = requests.get(url, headers={"x-token": self.x_token})
        data = r.json()
        return data

    def create_image_folder(self, folder_path: str):
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"Folder '{folder_path}' created.")
        else:
            print(f"Folder '{folder_path}' already exists")

    def main(self):
        self.create_image_folder(self.image_folder)
        end_date, start_date = self.calculate_date_range()
        end_date_str, start_date_str = end_date.strftime('%Y-%m-%d'), start_date.strftime('%Y-%m-%d')
        data = self.get_cara_entries(start_date_str, end_date_str, "500", "0")

        food_image_ids = [self.retrieve_image_id(x) for x in data['results']]

        # Group the entries by userDateTracking
        grouped_data = {}
        for entry in data["results"]:
            user_date = entry["userDateTracking"]
            if user_date in grouped_data:
                grouped_data[user_date].append(entry)
            else:
                grouped_data[user_date] = [entry]

        # Reverse the order of grouped_data based on the user_date (newest to oldest)
        sorted_grouped_data = dict(sorted(grouped_data.items(), reverse=True))

        # Create a Jinja2 environment and load the template from the file system
        template_env = Environment(loader=FileSystemLoader('templates'))
        template = template_env.get_template('food-diary.html')

        # Render the template with the data
        rendered_template = template.render(grouped_data=sorted_grouped_data)

        # Specify the file path where you want to save the HTML
        output_file_path = 'index.html'

        # Save the rendered HTML content to the file
        with open(output_file_path, 'w') as file:
            file.write(rendered_template)

if __name__ == '__main__':
    # Read the x_token value from the environment variable CARA_XTOKEN
    cara_xtoken = os.environ.get("CARA_XTOKEN")
    if cara_xtoken is None:
        # Handle the case when the environment variable is not set
        print("Please set your CARA_XTOKEN as environment variable.")
        exit(1)
    extractor = DataExtractor(x_token=cara_xtoken, number_of_days=180, json_file='cara.json', image_folder="images")
    extractor.main()
