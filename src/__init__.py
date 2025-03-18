import os
import sys
import json
import base64
import requests
from io import BytesIO
from datetime import datetime
from aqt import mw
from aqt.qt import Qt, QPushButton, QLabel, QLineEdit, QComboBox, QVBoxLayout, QHBoxLayout, QTextEdit, QDialog, QProgressBar, QThread, pyqtSignal
from aqt.utils import tooltip, showInfo
from anki.collection import Collection
from re import sub  # Import regular expression module

# Correctly set folder path to openai package and dependencies
dep_dir_name = 'lib'
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), dep_dir_name))

from openai import OpenAI
from PIL import Image

# Set working directory to script directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def log_error(error_message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open('error_log.txt', 'a') as log_file:
        log_file.write(f"{timestamp} - {error_message}\n")

def debug_log(log_data):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open('debug_log.txt', 'a') as log_file:
        log_file.write(f"{timestamp} - {log_data}\n")

def extract_numeric_value(text):
    return int(sub(r'\D', '', text))  # Remove non-digit characters

class GenerateImagesThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(int, int)
    cancel = pyqtSignal()  # Signal to notify cancellation

    def __init__(self, app, nids):
        QThread.__init__(self)
        self.app = app
        self.nids = nids
        self._is_running = True

    def run(self):
        success_count = 0
        error_count = 0

        for index, nid in enumerate(self.nids):
            if not self._is_running:
                break

            note = self.app.browser.mw.col.get_note(nid) # Replace getNote with get_note
            term_text = note[self.app.current_settings["Term Field"]]
            sentence_text = note[self.app.current_settings["Sentence Field"]]
            if sentence_text:
                prompt_sentence = sentence_text
            else:
                prompt_sentence = term_text
                

            # Create the prompt for the OpenAI API
            prompt = self.app.current_settings["Current Prompt"].format(term=term_text, sentence=prompt_sentence)

            # Call the OpenAI API
            try:
                image_url = self.app.generate_image_from_openai(prompt)
                if not image_url:
                    raise ValueError("Invalid image URL returned")

                # Save the image to Anki's media folder and get the file name
                media_folder = self.app.browser.mw.col.media.dir()
                image_filename = self.app.save_image_to_media_folder(image_url, media_folder)

                # Update the note with the new image
                self.app.update_note_image_field(note, image_filename)

                success_count += 1
            except (requests.RequestException, ValueError) as e:
                error_count += 1
                error_message = f"Error processing note {nid}: {e}"
                print(error_message)
                log_error(error_message)
            except Exception as e:
                error_count += 1
                error_message = f"Unhandled error processing note {nid}: {e}"
                print(error_message)
                log_error(error_message)

            self.progress.emit((index + 1) * 100 // len(self.nids))

        self.finished.emit(success_count, error_count)

    def cancel(self):
        self._is_running = False

class ProgressBarDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Processing")
        self.setModal(True)
        self.setFixedSize(300, 150)
        layout = QVBoxLayout()
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel)
        layout.addWidget(self.cancel_button)

        self.setLayout(layout)

    def set_thread(self, thread):
        self.thread = thread

    def cancel(self):
        if self.thread.isRunning():
            self.status_label.setText("Cancelling operation, please wait...")
            self.thread.cancel()

    def closeEvent(self, event):
        if self.thread.isRunning():
            self.thread.cancel()
        super().closeEvent(event)

class AIApp(QDialog):
    current_settings = {
        "Note Fields": [],
        "Sentence Field": "",
        "Term Field": "",
        "Image Field": "",
        "Resize Height": "",
        "Conflict Action": "",
        "API Key": "",
        "Default Prompt": "",
        "Current Prompt": "",
        "Base URL": "" # Add Base URL to current settings
    }

    def __init__(self, browser):
        super().__init__()
        self.browser = browser
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('DALL-E for Anki')
        self.setMinimumSize(500, 600)
        self.read_config()

        # Set main and sublayout styles
        self.main_layout = QVBoxLayout()
        self.dropdown_field_layout = QVBoxLayout()
        self.line_edit_layout = QVBoxLayout()
        self.button_layout = QHBoxLayout()

        self.sentence_dropdown_label = QLabel('Sentence Field')
        self.sentence_dropdown = QComboBox()

        self.term_dropdown_label = QLabel('Target Word Field')
        self.term_dropdown = QComboBox()

        self.write_image_label = QLabel('Image Field')
        self.write_image_field = QComboBox()

        self.resize_image_label = QLabel('Resize Images to Max Height:')
        self.resize_image_combo = QComboBox()
        resize_options = ['256px', '512px (RECOMMENDED)', '1024px (No resize)']
        self.resize_image_combo.addItems(resize_options)
        resize_index = self.fetch_resize_index()
        self.resize_image_combo.setCurrentIndex(resize_index)

        self.resize_image_advisement = QLabel('It is also possible to resize images by using custom CSS on your cards.  Reference readme for more info.')
        self.resize_image_advisement.setWordWrap(True)

        self.conflict_action_label = QLabel('If Image Field is not Empty:')
        self.conflict_action_combo = QComboBox()
        conflict_actions = ['Overwrite', 'Add', 'Skip']
        self.conflict_action_combo.addItems(conflict_actions)
        conflict_index = self.fetch_conflict_index()
        self.conflict_action_combo.setCurrentIndex(conflict_index)

        self.dropdown_field_layout.addWidget(self.sentence_dropdown_label)
        self.dropdown_field_layout.addWidget(self.sentence_dropdown)
        self.dropdown_field_layout.addWidget(self.term_dropdown_label)
        self.dropdown_field_layout.addWidget(self.term_dropdown)
        self.dropdown_field_layout.addWidget(self.write_image_label)
        self.dropdown_field_layout.addWidget(self.write_image_field)
        self.dropdown_field_layout.addWidget(self.resize_image_label)
        self.dropdown_field_layout.addWidget(self.resize_image_combo)
        self.dropdown_field_layout.addWidget(self.resize_image_advisement)
        self.dropdown_field_layout.addWidget(self.conflict_action_label)
        self.dropdown_field_layout.addWidget(self.conflict_action_combo)

        self.api_key_label = QLabel('OpenAI API Key')
        self.api_key_field = QLineEdit()
        self.api_key_field.setPlaceholderText('Enter your secret API key with no quotes')
        api_key = self.fetch_api_key()
        self.api_key_field.setText(api_key)

        # Add Base URL UI element
        self.base_url_label = QLabel('Base URL (Optional)')
        self.base_url_field = QLineEdit()
        self.base_url_field.setPlaceholderText('Enter custom Base URL (optional)')
        base_url = self.fetch_base_url()
        self.base_url_field.setText(base_url)

        self.prompt_label = QLabel('DALL-E Prompt')
        self.prompt_field = QTextEdit()
        self.prompt_field.setFixedHeight(100)  # Adjusted height
        prompt = self.set_display_prompt()
        self.prompt_field.setText(prompt)
        self.prompt_field.textChanged.connect(self.update_current_prompt)
        self.prompt_field_key = QLabel('Note: longer prompts will consume more tokens and may increase cost of API request. DALL-E-3 automatically rewrites user prompts to improve results and so very verbose prompts/excessive prompt engineering is usually not necessary.')
        self.prompt_field_key.setWordWrap(True)

        self.line_edit_layout.addWidget(self.api_key_label)
        self.line_edit_layout.addWidget(self.api_key_field)
        # Add Base URL to layout
        self.line_edit_layout.addWidget(self.base_url_label)
        self.line_edit_layout.addWidget(self.base_url_field)
        self.line_edit_layout.addWidget(self.prompt_label)
        self.line_edit_layout.addWidget(self.prompt_field)
        self.line_edit_layout.addWidget(self.prompt_field_key)

        self.exit_button = QPushButton('Save and Exit')
        self.exit_button.clicked.connect(self.exit_and_save)
        self.default_button = QPushButton('Default Prompt')
        self.default_button.clicked.connect(self.reset_prompt)
        self.generate_button = QPushButton('Generate')
        self.generate_button.clicked.connect(self.process_notes)
        self.button_layout.addWidget(self.exit_button)
        self.button_layout.addWidget(self.default_button)
        self.button_layout.addWidget(self.generate_button)

        self.main_layout.addLayout(self.dropdown_field_layout)
        self.main_layout.addLayout(self.line_edit_layout)
        self.main_layout.addLayout(self.button_layout)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setLayout(self.main_layout)

        self.populate_dropdowns()  # Populate dropdowns after they are created

    def showEvent(self, event):
        self.update_fields_dict()
        super().showEvent(event)

    def closeEvent(self, event):
        self.exit_and_save()
        super().closeEvent(event)

    def read_config(self):
        try:
            with open('config.json', 'r') as config:
                config_data = json.load(config)
                AIApp.current_settings.update(config_data)
        except FileNotFoundError:
            print('No config JSON was located.')
        except PermissionError:
            print('Permission Error.')

    def set_display_prompt(self):
        if AIApp.current_settings["Current Prompt"] == "":
            prompt = AIApp.current_settings["Default Prompt"]
        else:
            prompt = AIApp.current_settings["Current Prompt"]
        return prompt

    def reset_prompt(self):
        self.prompt_field.setText(AIApp.current_settings["Default Prompt"])

    def fetch_api_key(self):
        if AIApp.current_settings["API Key"] != "":
            return AIApp.current_settings["API Key"]
        else:
            return ""
    
    # Fetch Base URL from config
    def fetch_base_url(self):
        return AIApp.current_settings.get("Base URL", "")

    def fetch_conflict_index(self):
        if AIApp.current_settings["Conflict Action"] != "":
            return AIApp.current_settings["Conflict Action"]
        else:
            return 0

    def fetch_resize_index(self):
        if AIApp.current_settings["Resize Height"] != "":
            return AIApp.current_settings["Resize Height"]
        else:
            return 1

    def exit_and_save(self):
        AIApp.current_settings["Current Prompt"] = self.prompt_field.toPlainText()
        AIApp.current_settings["API Key"] = self.api_key_field.text()
        AIApp.current_settings["Term Field"] = self.term_dropdown.currentText()
        AIApp.current_settings["Sentence Field"] = self.sentence_dropdown.currentText()
        AIApp.current_settings["Image Field"] = self.write_image_field.currentText()
        AIApp.current_settings["Conflict Action"] = self.conflict_action_combo.currentIndex()
        AIApp.current_settings["Resize Height"] = self.resize_image_combo.currentIndex()
        # Save Base URL
        AIApp.current_settings["Base URL"] = self.base_url_field.text()

        with open('config.json', 'w') as config:
            json.dump(AIApp.current_settings, config, indent=4)
        self.close()

    def get_selected_note_ids(self):
        nids = self.browser.selectedNotes()
        if not nids:
            tooltip('No cards selected.')
            return []
        return nids

    def get_note_fields(self):
        nids = self.get_selected_note_ids()
        if not nids:
            return []
        sample_nid = nids[0]
        mw = self.browser.mw
        # Replace getNote with get_note
        note = mw.col.get_note(sample_nid)
        # Replace model with note_type
        model = note.note_type()
        # Replace fieldNames with field_names
        fields = mw.col.models.field_names(model)
        return fields

    def populate_dropdowns(self):
        fields = AIApp.current_settings["Note Fields"]
        self.sentence_dropdown.addItems(fields)
        self.term_dropdown.addItems(fields)
        self.write_image_field.addItems(fields)

    def update_fields_dict(self):
        new_fields = set(self.get_note_fields())

        # Only update settings if the new fields are different
        if set(AIApp.current_settings["Note Fields"]) != new_fields:
            AIApp.current_settings["Note Fields"] = list(new_fields)

        # Save current selections
        current_sentence = self.sentence_dropdown.currentText()
        current_term = self.term_dropdown.currentText()
        current_image = self.write_image_field.currentText()

        # Clear and update dropdown items
        self.sentence_dropdown.clear()
        self.term_dropdown.clear()
        self.write_image_field.clear()

        self.populate_dropdowns()

        # Restore previous selections if they still exist
        if current_sentence in AIApp.current_settings["Note Fields"]:
            self.sentence_dropdown.setCurrentText(current_sentence)
        if current_term in AIApp.current_settings["Note Fields"]:
            self.term_dropdown.setCurrentText(current_term)
        if current_image in AIApp.current_settings["Note Fields"]:
            self.write_image_field.setCurrentText(current_image)

        # Ensure the dropdowns reflect the stored settings if nothing was selected
        if isinstance(AIApp.current_settings["Sentence Field"], str) and AIApp.current_settings["Sentence Field"] in AIApp.current_settings["Note Fields"]:
            self.sentence_dropdown.setCurrentText(AIApp.current_settings["Sentence Field"])
        if isinstance(AIApp.current_settings["Term Field"], str) and AIApp.current_settings["Term Field"] in AIApp.current_settings["Note Fields"]:
            self.term_dropdown.setCurrentText(AIApp.current_settings["Term Field"])
        if isinstance(AIApp.current_settings["Image Field"], str) and AIApp.current_settings["Image Field"] in AIApp.current_settings["Note Fields"]:
            self.write_image_field.setCurrentText(AIApp.current_settings["Image Field"])

    def update_current_prompt(self):
        AIApp.current_settings["Current Prompt"] = self.prompt_field.toPlainText()

    def process_notes(self):
        # Fetch current settings from the dialog
        self.current_settings["API Key"] = self.api_key_field.text()
        self.current_settings["Term Field"] = self.term_dropdown.currentText()
        self.current_settings["Sentence Field"] = self.sentence_dropdown.currentText()
        self.current_settings["Image Field"] = self.write_image_field.currentText()
        self.current_settings["Conflict Action"] = self.conflict_action_combo.currentIndex()
        self.current_settings["Resize Height"] = self.resize_image_combo.currentIndex()
        # Fetch Base URL
        self.current_settings["Base URL"] = self.base_url_field.text()

        nids = self.get_selected_note_ids()
        if not nids:
            return
        
        # Initialize OpenAI client with Base URL if provided
        api_key = self.current_settings["API Key"]
        base_url = self.current_settings["Base URL"]
        self.client = OpenAI(api_key=api_key, base_url=base_url if base_url else None)

        self.progress_dialog = ProgressBarDialog(self)
        self.thread = GenerateImagesThread(self, nids)
        self.progress_dialog.set_thread(self.thread)
        
        self.progress_dialog.show()

        # Start the background thread for processing notes
        self.thread.progress.connect(self.progress_dialog.progress_bar.setValue)
        self.thread.finished.connect(self.on_processing_finished)
        self.thread.start()

    def generate_image_from_openai(self, prompt):
        try:
            response = self.client.images.generate(
                model='dall-e-3',
                size='1024x1024',
                prompt=prompt
            )
            return response.data[0].url
        except Exception as e:
            error_message = f"OpenAI API error: {e}"
            print(error_message)
            log_error(error_message)
            return None

    def save_image_to_media_folder(self, image_url, media_folder):
        try:
            # Download the image from the URL
            response = requests.get(image_url)
            image_data = response.content

            # Resize the image if required
            resize_height = self.current_settings["Resize Height"]
            if resize_height != 2:  # Not '1024px (No resize)'
                image = Image.open(BytesIO(image_data))
                width, height = image.size

                # Extract the numeric value for resizing
                new_height = extract_numeric_value(self.resize_image_combo.currentText())
                new_width = int(new_height * width / height)
                image = image.resize((new_width, new_height), Image.LANCZOS)

                buffer = BytesIO()
                image.save(buffer, format="PNG")
                image_data = buffer.getvalue()

            # Generate a unique filename
            image_filename = f"{base64.urlsafe_b64encode(os.urandom(6)).decode('utf-8')}.png"
            full_path = os.path.join(media_folder, image_filename)

            # Save the image to the media folder
            with open(full_path, 'wb') as image_file:
                image_file.write(image_data)

            return image_filename
        except Exception as e:
            error_message = f"Error saving image: {e}"
            print(error_message)
            log_error(error_message)
            return None

    def update_note_image_field(self, note, image_filename):
        try:
            current_image_field = note[self.current_settings["Image Field"]]
            if self.current_settings["Conflict Action"] == 0:  # Overwrite
                note[self.current_settings["Image Field"]] = f"<img src='{image_filename}' />"
            elif self.current_settings["Conflict Action"] == 1:  # Add
                note[self.current_settings["Image Field"]] += f" <img src='{image_filename}' />"
            elif self.current_settings["Conflict Action"] == 2:  # Skip
                if current_image_field.strip() == "":
                    note[self.current_settings["Image Field"]] = f"<img src='{image_filename}' />"

            note.add_tag('ai-img') # Replace addTag with add_tag
            self.browser.mw.col.update_note(note)  # Replace flush with update_note
        except Exception as e:
            error_message = f"Error updating note {note.id}: {e}"
            print(error_message)
            log_error(error_message)

    def on_processing_finished(self, success_count, error_count):
        self.progress_dialog.close()
        showInfo(f"Processing finished: {success_count} successes, {error_count} errors.")

#################    Initialization   #####################

app_instance = None

def show_ai_app(browser):
    global app_instance
    if app_instance is None:
        app_instance = AIApp(browser)
    app_instance.update_fields_dict()
    app_instance.exec()

def setup_menu(browser):
    menu = browser.form.menuEdit
    menu.addSeparator()
    option = menu.addAction('Add DALL-E Images')
    option.triggered.connect(lambda _, b=browser: show_ai_app(b))

from aqt.gui_hooks import browser_will_show
browser_will_show.append(setup_menu)