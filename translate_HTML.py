import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from translatepy.translators.google import GoogleTranslate
from bs4 import BeautifulSoup, Comment
import warnings
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from urllib3.util import Retry
from requests.adapters import HTTPAdapter
import chinese_converter

languages = {
    'afrikaans': 'af',
    'albanian': 'sq',
    'amharic': 'am',
    'arabic': 'ar',
    'armenian': 'hy',
    'azerbaijani': 'az',
    'basque': 'eu',
    'belarusian': 'be',
    'bengali': 'bn',
    'bosnian': 'bs',
    'bulgarian': 'bg',
    'catalan': 'ca',
    'cebuano': 'ceb',
    'chinese (simplified)': 'zh',
    'chinese (traditional)': 'zh-TW',
    'corsican': 'co',
    'croatian': 'hr',
    'czech': 'cs',
    'danish': 'da',
    'dutch': 'nl',
    'english': 'en',
    'esperanto': 'eo',
    'estonian': 'et',
    'filipino': 'tl',
    'finnish': 'fi',
    'french': 'fr',
    'frisian': 'fy',
    'galician': 'gl',
    'georgian': 'ka',
    'german': 'de',
    'greek': 'el',
    'gujarati': 'gu',
    'haitian creole': 'ht',
    'hausa': 'ha',
    'hawaiian': 'haw',
    'hebrew': 'he',
    'hindi': 'hi',
    'hmong': 'hmn',
    'hungarian': 'hu',
    'icelandic': 'is',
    'igbo': 'ig',
    'indonesian': 'id',
    'irish': 'ga',
    'italian': 'it',
    'japanese': 'ja',
    'javanese': 'jv',
    'kannada': 'kn',
    'kazakh': 'kk',
    'khmer': 'km',
    'korean': 'ko',
    'kurdish': 'ku',
    'kyrgyz': 'ky',
    'lao': 'lo',
    'latin': 'la',
    'latvian': 'lv',
    'lithuanian': 'lt',
    'luxembourgish': 'lb',
    'macedonian': 'mk',
    'malagasy': 'mg',
    'malay': 'ms',
    'malayalam': 'ml',
    'maltese': 'mt',
    'maori': 'mi',
    'marathi': 'mr',
    'mongolian': 'mn',
    'myanmar': 'my',
    'nepali': 'ne',
    'norwegian': 'no',
    'nyanja': 'ny',
    'oriya': 'or',
    'pashto': 'ps',
    'persian': 'fa',
    'polish': 'pl',
    'portuguese': 'pt',
    'punjabi': 'pa',
    'romanian': 'ro',
    'russian': 'ru',
    'samoan': 'sm',
    'scots gaelic': 'gd',
    'serbian': 'sr',
    'sesotho': 'st',
    'shona': 'sn',
    'sindhi': 'sd',
    'sinhala': 'si',
    'slovak': 'sk',
    'slovenian': 'sl',
    'somali': 'so',
    'spanish': 'es',
    'sundanese': 'su',
    'swahili': 'sw',
    'swedish': 'sv',
    'tajik': 'tg',
    'tamil': 'ta',
    'telugu': 'te',
    'thai': 'th',
    'turkish': 'tr',
    'ukrainian': 'uk',
    'urdu': 'ur',
    'uyghur': 'ug',
    'uzbek': 'uz',
    'vietnamese': 'vi',
    'welsh': 'cy',
    'xhosa': 'xh',
    'yiddish': 'yi',
    'yoruba': 'yo',
    'zulu': 'zu'    
}


# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Suppress BeautifulSoup warnings
warnings.filterwarnings("ignore", category=UserWarning, module='bs4')

class CustomGoogleTranslate(GoogleTranslate):
    def __init__(self):
        super().__init__()
        self.session = requests.Session()
        retry = Retry(connect=3, backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.verify = False  # Disable SSL verification

def get_html_files(directory):
    """Recursively get all HTML files in the given directory."""
    html_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.html'):
                html_files.append(os.path.join(root, file))
    return html_files

def translate_content(content, translator, source_language, target_language):
    """Translate content using the provided translator."""
    try:
        if source_language == "zh" and target_language == "zh-TW":
            translated = chinese_converter.to_traditional(content)
        elif source_language == "zh-TW" and target_language == "zh":
            translated = chinese_converter.to_simplified(content)
        elif source_language == "zh-TW" and target_language != "zh":
            content = chinese_converter.to_simplified(content)
            source_language = "zh"
            translated = translator.translate(content, source_language=source_language, destination_language=target_language).result
        elif source_language != "zh" and target_language == "zh-TW":
            target_language = "zh"
            translated = translator.translate(content, source_language=source_language, destination_language=target_language).result
            translated = chinese_converter.to_traditional(translated)
        else:
            translated = translator.translate(content, source_language=source_language, destination_language=target_language).result
        return translated
    except Exception as e:
        logging.error(f"Translation error: {e}")
        return content

def process_html_file(html_file, translator, source_language, target_language):
    """Process a single HTML file: read, translate, and write back the content."""
    try:
        with open(html_file, 'r', encoding='utf-8') as file:
            soup = BeautifulSoup(file, 'lxml')
        
        # Translate placeholders in input tags
        for input_tag in soup.find_all('input'):
            if 'placeholder' in input_tag.attrs:
                input_tag['placeholder'] = translate_content(input_tag['placeholder'], translator, source_language, target_language)

        # Translate visible text, excluding specific tags and comments
        for element in soup.find_all():
            if element.name not in ['style', 'script']:
                for content in element.contents:
                    if isinstance(content, str) and content.strip() and not isinstance(content, Comment):
                        logging.info(f"Translating {element.name} of {os.path.basename(html_file)}")
                        translated_text = translate_content(content, translator, source_language, target_language)
                        content.replace_with(translated_text)

        # Write the translated content back to the file
        with open(html_file, 'w', encoding='utf-8') as file:
            file.write(str(soup))
        
        return html_file

    except Exception as e:
        logging.error(f"Failed to process {html_file}: {e}")
        return None

def start_translation(source_language, target_language, directory):
    html_files = get_html_files(directory)    
    logging.info(f"Found {len(html_files)} HTML files to process.")

    translator = CustomGoogleTranslate()

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_html_file, html_file, translator, source_language, target_language): html_file for html_file in html_files}
        
        for future in as_completed(futures):
            html_file = futures[future]
            try:
                future.result()
            except Exception as e:
                logging.error(f"Error processing {html_file}: {e}")

    messagebox.showinfo("Translation Complete", "All HTML files have been processed successfully.")



def create_gui():
    global languages
    #     Create the main window
    root = tk.Tk()
    root.title("HTML Translator")
    root.geometry("760x230")

    # Configure styles
    style = ttk.Style()
    style.configure("TLabel", font=("Helvetica", 14))
    style.configure("TButton", font=("Helvetica", 14))
    style.configure("TCombobox", font=("Helvetica", 14))

    # Directory selection
    directory_label = ttk.Label(root, text="Select Parent Folder:")
    directory_label.grid(column=0, row=0, padx=10, pady=10)

    directory_path = tk.StringVar()

    def browse_directory():
        directory = filedialog.askdirectory()
        directory_path.set(directory)

    directory_entry = ttk.Entry(root, textvariable=directory_path, width=60)
    directory_entry.grid(column=1, row=0, padx=10, pady=10)

    browse_button = ttk.Button(root, text="Browse", command=browse_directory)
    browse_button.grid(column=2, row=0, padx=10, pady=10)



    # Enable type-to-filter functionality for comboboxes
    def set_autocomplete(combobox):
        def on_key_release(event):
            value = combobox.get().lower()
            if value == '':
                combobox['values'] = list(languages.keys())
            else:
                data = [item for item in languages.keys() if item.lower().startswith(value)]
                combobox['values'] = data
                combobox.event_generate('<Down>')


        combobox.bind('<KeyRelease>', on_key_release)



    # Create and place the source language label and combobox
    source_label = ttk.Label(root, text="Source Language:")
    source_label.grid(column=0, row=1, padx=10, pady=10)

    source_combobox = ttk.Combobox(root, values=list(languages.keys()), state="normal")
    source_combobox.grid(column=1, row=1, padx=10, pady=10)

    set_autocomplete(source_combobox)


    # Create and place the target language label and combobox
    target_label = ttk.Label(root, text="Target Language:")
    target_label.grid(column=0, row=2, padx=10, pady=10)

    target_combobox = ttk.Combobox(root, values=list(languages.keys()), state="normal")
    target_combobox.grid(column=1, row=2, padx=10, pady=10)

    set_autocomplete(target_combobox)

    target_combobox.option_add('*TCombobox*Listbox.font', ('Helvetica', 14))

    # Define the function to start translation when the button is clicked
    def on_translate_button_click():
        source_language = languages[source_combobox.get()]
        target_language = languages[target_combobox.get()]
        directory = directory_path.get()
        if directory:
            start_translation(source_language, target_language, directory)
        else:
            messagebox.showerror("Error", "Please select a directory.")

    # Create and place the translate button
    translate_button = ttk.Button(root, text="Translate", command=on_translate_button_click)
    translate_button.grid(column=0, row=3, columnspan=3, pady=20)

    # Start the Tkinter event loop
    root.mainloop()


if __name__ == "__main__":
    create_gui()