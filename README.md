# dalle3-for-anki
 An Anki addon which allows bulk generation of images from OpenAI's DALL-E-3 API.

- [dalle3-for-anki](#dalle3-for-anki)
  - [⚙ Installation](#-installation)
    - [🌎 OpenAI API Access](#-openai-api-access)
      - [API Funding](#api-funding)
  - [💻 Usage](#-usage)
    - [🖼 Resizing Images](#-resizing-images)
    - [✎ Prompt Editing](#-prompt-editing)
    - [🦾 Advanced Usage](#-advanced-usage)
  - [❌ Troubleshooting and Errors](#-troubleshooting-and-errors)
  - [Licensing and Acknowledgements](#licensing-and-acknowledgements)


## &#9881; Installation

You can download the latest version of the addon from the [Releases](https://github.com/ccos89/dalle3-for-anki/releases/) tab.  You can double-click the .ankiaddon file to initiate the install dialog, or you can open Anki->Tools->Add-ons->Install from File.

This addon is also available for download on [Ankiweb](https://ankiweb.net/shared/info/1651931833).

You can also package your own version of the addon by cloning/downloading this repository and compressing the contents of the \src folder into a .zip folder.  The contents of the \src folder must be the top level of the .zip folder (no intermediary folder).  You can then just rename the .zip extension to .ankiaddon and you will have an Anki addon.  This is useful if you want to edit the underlying code (see [Advanced Usage](#advanced-usage)).

*I have tested this addon with Windows 10 and 11 in both Qt6 and Qt5 versions of Anki 24.04.1 without issues.  I do not have access to MacOS and do not have a Linux box set up properly to test support there, so Windows is the only official OS I can support, but I don't see any reason why it wouldn't work elsewhere. I am open to accept PRs to fix any issues that arise.*


### 	&#127758; OpenAI API Access

&#128204; This addon requires an OpenAI API Key to function.  &#128204;

To obtain an API key, you can create or login to an account at [OpenAI](https://platform.openai.com/).  Once you create your account, navigate to the 'Dashboard' section of the API portion of the site (top right hand corner).  You can create a new 'Project' if desired or just use the default project.  

In the left sidebar menu click on the API key option.  Click the green Create API Key button in the top right, name the key if desired, and keep the other options as their defaults.  The program will display your API key for you to copy.

&#9888; You must write down or save your API key to a text file right away.  If you close the popup you will not be able to view the key again. 

If you lose your API key you can just create another one with no issues.

#### API Funding

You will also need to add funding to your API account to continue to use the service.  This is separate than any subscription you may have to ChatGPT.  To add funding, click on the settings cogwheel in the top right hand corner of the API corner of the site, then access Billing from the left sidebar menu.  

Once you add a card to your account you can set it to automatically add funds as needed or you can just add funds as needed manually.  I recommend you just add money manually so you can't accidentally spend way more than you anticipated.

You can also set a spending limit on your 'Project' where you generated your API key, which I highly recommend doing to avoid overspending.

&#9888; I have no affiliation with OpenAI.  This program is being provided as a means of accessing their API and any financial transactions are directly between you and OpenAI and I have no part in them.  Make sure you are responsibly restricting the funds you allow OpenAI to access so you do not accidentally charge more than you want to your card, as I have no recourse and no liability for your financial transactions with OpenAI.

## 	&#128187; Usage

To use the addon, open the Card Browser in Anki, select the cards you want to add/replace images on, and click Edit->Add DALL-E Images from the top menu.  Select the appropriate fields to read the Target Word and Target Sentence from and to write the resulting image to.  

&#9888; Only attempt to edit one 'Note Type' at a time, as this program works by reading the available fields from the selected Note Type.  Attempting to modify multiple Note Types simulataneously will almost certainly induce an error.

You must paste your OpenAI API key into the API Key field for the program to work.

You can also select what behavior you want to occur if the target image field already has an image in it (overwrite, skip, add).

### &#x1f5bc; Resizing Images

DALL-E-3 only generates images in 1024x1024, which is too large for practical use in normal Anki usage scenarios.  The images can be resized in two ways:

1) You can add custom CSS to your Note Type which sets a max display size for the image field on your card.  This does not affect the size of the underlying image in your media collection, only the displayed size.
   
2) You can use the resize dropdown in this program which resizes the image generated by DALL-E prior to saving it to your media collection.  This reduces the size of the image in your media collection leading to quicker syncing, but you will lose the higher-resolution image generated by DALL-E.

**I recommended using the 512x512 resize option for a sweet spot of size and quality.**

### &#9998; Prompt Editing 

You can modify the prompt that is sent to DALL-E by changing the text in the prompt box.

&#9888; **You must include the wildcards {term} and {sentence} in your prompt for the fields from your card to be passed correctly to the API.**

DALL-E-3 automatically rewrites the prompt you give it, which negates a lot of the need for verbose or complex prompt engineering commonly associated with models like Stable Diffusion.  From the [OpenAI API Documentation](https://platform.openai.com/docs/guides/images/image-generation):

>'With the release of DALL·E 3, the model now takes in the default prompt provided and automatically re-write it for safety reasons, and to add more detail (more detailed prompts generally result in higher quality images). While it is not currently possible to disable this feature, you can use prompting to get outputs closer to your requested image by adding the following to your prompt: I NEED to test how the tool works with extremely simple prompts. DO NOT add any detail, just use it AS-IS:.'

Keep in mind that longer prompts will require more tokens, leading to a higher cost.  For more information see the [OpenAI Tokenizer](https://platform.openai.com/tokenizer).

At any time you can reset to the Default Prompt by using the Default Prompt button.  The default prompt can also be modified - see Advanced Usage below.

### 	&#129470; Advanced Usage

The saved options for the addon can also be accessed and modified by going to the Anki Addons menu, highlighting this addon, and clicking the Config button which will pull up the content of the config.json file.  The default prompt can be edited by editing the following key/value pair:

```
"Default Prompt": "A masterwork, captivating and gorgeous work of art in any medium or style of the following: {sentence}.  The work completely captures the essence of {term}. The work focuses purely on the visual representation of the theme and has no text.",
```

If you package your own version of the addon (see [Installation](#installation) section above) you can modify the underlying request that is sent to the API to change the model to DALL-E-2, change the resolution of the images, etc.  Edit the following function in the __init__.py file:

```
    def generate_image_from_openai(self, prompt):
        try:
            response = self.client.images.generate(
                model='dall-e-3',
                size='1024x1024',
                prompt=prompt
            )
```

For information on what valid arguments and values you can pass to this function, please reference the [OpenAI API Documentation](https://platform.openai.com/docs/guides/images/image-generation).

## &#10060; Troubleshooting and Errors

&#128013; I am new to Python and programming in general so please be kind :) This is my first real project.  &#128013;

Errors that occur during processing are logged in an error.txt file in the addon's directory.  To easily access the file, navigate to Anki's Addons menu, highlight this addon, and click 'View Files'.

Common errors include:

**Content Policy Violation** - *Their system is super overly sensitive.  Don't worry too much about a ban or suspension if you see this, unless the vast majority of your requests are violations you should be fine.*

**Insufficient Funds** - *You need to add additional funding to your OpenAI account to proceed, or you have set a spending limit for your 'project' wherein your secret key is derived.  Give it a few minutes after you add money or update your spending limit for the changes to kick in.*

**Rate Limit** - *OpenAI rate limits access to their API based on your usage tier. For more information reference the [OpenAI API Documentation](https://platform.openai.com/docs/guides/rate-limits).  You shouldn't run into this unless you have a lot of failed generations, in which case it will course-correct as generations start to succeed again.*

Your error log will also include the nid, which is the note ID of the specific card where the error occurred.  You can search in the Anki browser window for this note ID to identify the problem note.

***

Please try to reference the error log and remediate the problem - if you aren't able to solve the problem, you are welcome to open an Issue here on Github and I will do my best to help you.  If you do open an issue please include your error log text file, your OS, what version of Anki you are running (including which Qt version), and if possible details about the card causing the issue.

I have tested the addon across multiple Windows machines without issue - it should work across any standard OS, but I don't have access to a MacOS device to test it.

**Pull Requests are welcome.** &#x1f44d;

## Licensing and Acknowledgements

Please refer to the LICENSE file for this application's licensing.

This application bundles dependencies to be able to work with Anki.  Copies of these packages' dependencies can be found in the dep-licenses folder.

I would like to also thank and acknowledge the excellent addons [Batch Download Pictures from Google Images](https://ankiweb.net/shared/info/561924305) and [Generate Batch Audio for Anki](https://github.com/DillonWall/generate-batch-audio-anki-addon) for inspiration and code reference.
