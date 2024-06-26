from flask import Flask, request, jsonify
from flask_cors import CORS
from moviepy.editor import VideoFileClip
from collections import Counter
import nltk
nltk.download('vader_lexicon')
import speech_recognition as sr
from nltk.sentiment import SentimentIntensityAnalyzer
import cv2
import numpy as np
from roboflow import Roboflow
from AudioSenti import analyze_sentiment
from StutterCheck import analyze_stutter
import os
import shutil


rf = Roboflow(api_key="LF4lxbBefvMh8W3awrgv")

project_f = rf.workspace().project("face-emotion-s9kw9")
model_f = project_f.version(1).model

project_d = rf.workspace().project("dress-model-gknib")
model_d = project_d.version(1).model


def empty_folder(folder_path):
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        # Iterate over all the files and directories in the folder
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            try:
                # Check if it is a file or directory
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)  # Remove the file or link
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)  # Remove the directory
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')
    else:
        print(f'The folder {folder_path} does not exist or is not a directory.')
def highest_confidence_class(predictions):
    max_confidence = float('-inf')
    max_class = None
    
    for prediction in predictions:
        if 'predictions' in prediction:
            for class_name, data in prediction['predictions'].items():
                confidence = data.get('confidence', 0)
                if confidence > max_confidence:
                    max_confidence = confidence
                    max_class = class_name
    
    return max_class

def save_frames_as_images(video_file):
    cap = cv2.VideoCapture(video_file)
    frame_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = int(0.1 * frame_total)
    image_fol = "images"
    if not os.path.exists(image_fol):
        os.makedirs(image_fol)
    
    for i in range(0,frame_total,step):
        cap.set(1, i)
        ret, frame = cap.read()
        if not ret:
            break
        cv2.imwrite(f"{image_fol}/frame_{i}.jpg", frame)


def get_best(model, video):
    save_frames_as_images(video)
    image_folder = "images"
    result_list = []
    for filename in os.listdir(image_folder):
        if filename.endswith(".jpg"):
            image_path = os.path.join(image_folder, filename)
            predictions = model.predict(image_path).json()['predictions']
            result = highest_confidence_class(predictions)
            result_list.append(result)
    
    return Counter(result_list).most_common(1)[0][0]



app=Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route('/')
def home():
  return jsonify({"hello":"world"})
@app.route('/upload',methods=['POST'])
def upload():
  if request.method=='POST':
    if 'video' not in request.files:
            return jsonify({"error": "No file part"})
    vid = request.files['video']
    if vid.filename == '':
        return jsonify({"error": "a error occured"})

    vid.save('temp.mp4')
    vid_path='temp.mp4'

    vidf=VideoFileClip(vid_path)
    aud=vidf.audio

    aud.write_audiofile('temp.wav')
    audf='temp.wav'


    emotion=get_best(model_f,vid_path)[1::]
    dress_code=get_best(model_d,vid_path)
    try:
        sentiment=analyze_sentiment(audf)
    except(sr.UnknownValueError):
        sentiment="No speech detected"
    stutter=analyze_stutter(audf)


    if dress_code=="0Coat" or dress_code=="1Shirt":
        dress="Formal"
    else:
        dress="Informal"

  empty_folder("images")
  
  return jsonify({"Emotion":emotion,
                  "Dress":dress,
                  "Sentiment":sentiment,
                  "Stutter":stutter})

if __name__=='__main__':
  app.run(debug=True)
