from flask import Blueprint, render_template

settings_views = Blueprint('settings_views', __name__, template_folder='../templates')


'''
Page Routes
'''

@settings_views.route('/settings', methods=['GET'])
def get_settings_page():
    return render_template('settings.html')