from flask import Flask, render_template, request
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import SubmitField, IntegerField, SelectField
from flask_wtf.recaptcha import RecaptchaField
from werkzeug.utils import secure_filename
from PIL import Image
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['RECAPTCHA_USE_SSL'] = False
app.config['RECAPTCHA_PUBLIC_KEY'] = '6Lc0F7ojAAAAAAFH7xmExcTim17I_fkxbg-OU5Qj'
app.config['RECAPTCHA_PRIVATE_KEY'] = '6Lc0F7ojAAAAAFtMRYaCaXYSmk4sDDrZKU2Zl2Kp'
app.config['RECAPTCHA_OPTIONS'] = {'theme': 'white'}

Bootstrap(app)

class ImageForm(FlaskForm):
    upload = FileField('Загрузите изображение', validators=[
        FileRequired(),
        FileAllowed(['jpg', 'png', 'jpeg'], 'Только изображения!')
    ])
    shift_pixels = IntegerField('Масштаб изображения', default=3)
    graph_toggle = SelectField('Показать графики', choices=[('both', 'Оба'), ('original', 'Только начальное изображение'), ('upped', 'Только обработанное изображение'), ('No', 'Не выводить')], default='both')
    #recaptcha = RecaptchaField()
    submit = SubmitField('Отправить')

def resize_image(image_path, shift_pixels):
    original_img = Image.open(image_path)

    original_width, original_height = original_img.size

    new_width = int(original_width * shift_pixels)
    new_height = int(original_height * shift_pixels)
    
    if new_width <= 0 or new_height <= 0:
        raise ValueError("Коэффициент масштабирования слишком мал.")

    upped_img = original_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    img_array = np.array(upped_img)
    upped_img = Image.fromarray(img_array)
    
    return upped_img

def reduce_image(image_path, original_width, original_height):
    upped_img = Image.open(image_path)
    reduced_img = upped_img.resize((original_width, original_height), Image.Resampling.LANCZOS)
    return reduced_img

def calculate_pixel_difference(original_image_path, reduced_image_path):
    original_img = np.array(Image.open(original_image_path).convert('RGB'))
    reduced_img = np.array(Image.open(reduced_image_path).convert('RGB'))

    if original_img.shape != reduced_img.shape:
        raise ValueError("Изображения должны иметь одинаковый размер.")

    difference = np.sum(np.abs(original_img - reduced_img))
    return difference

def plot_color_distribution(image_path, suffix):
    img = Image.open(image_path)
    img = img.convert('RGB')

    r, g, b = img.split()
    r_data = list(r.getdata())
    g_data = list(g.getdata())
    b_data = list(b.getdata())

    plt.figure()
    plt.hist(r_data, bins=256, color='red', alpha=0.5, label='Red')
    plt.hist(g_data, bins=256, color='green', alpha=0.5, label='Green')
    plt.hist(b_data, bins=256, color='blue', alpha=0.5, label='Blue')
    plt.legend()
    plt.title('Color Distribution')
    plt.xlabel('Color Value')
    plt.ylabel('Frequency')

    plot_path = os.path.join(app.config['UPLOAD_FOLDER'], f'color_distribution_{suffix}.png')
    plt.savefig(plot_path)
    plt.close()

    return plot_path

@app.route('/', methods=['GET', 'POST'])
def index():
    form = ImageForm()
    if form.validate_on_submit():
        file = form.upload.data
        shift_pixels = form.shift_pixels.data
        graph_toggle = form.graph_toggle.data
        filename = secure_filename(file.filename)
        original_image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(original_image_path)

        # Загрузка оригинального изображения и получение его размеров
        original_img = Image.open(original_image_path)
        original_width, original_height = original_img.size

        # Увеличение изображения
        upped_image = resize_image(original_image_path, shift_pixels)
        upped_image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'upped_' + filename)
        upped_image.save(upped_image_path)

        # Уменьшение масштаба до исходного размера
        reduced_image = reduce_image(upped_image_path, original_width, original_height)
        reduced_image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'reduced_' + filename)
        reduced_image.save(reduced_image_path)

        # Вычисление суммарной абсолютной разности
        pixel_difference = calculate_pixel_difference(original_image_path, reduced_image_path)

        # Построение гистограмм
        plot_path_original = plot_color_distribution(original_image_path, 'original') if graph_toggle in ['both', 'original'] else None
        plot_path_upped = plot_color_distribution(upped_image_path, 'upped') if graph_toggle in ['both', 'upped'] else None

        return render_template(
            'index.html',
            form=form,
            original_image=original_image_path,
            upped_image=upped_image_path,
            reduced_image=reduced_image_path,
            plot_image_original=plot_path_original,
            plot_image_upped=plot_path_upped,
            graph_toggle=graph_toggle,
            shift_pixels=shift_pixels,
            pixel_difference=pixel_difference
        )

    return render_template('index.html', form=form, graph_toggle='both', shift_pixels=3)