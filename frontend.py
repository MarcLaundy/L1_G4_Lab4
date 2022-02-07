import dash
from dash import dcc, html, callback_context
import dash_daq as daq
from dash.dependencies import Input, Output, State
from backend import Backend, logger
from mydbconfig import *
import random

backend = Backend(config, email, firstname, lastname)
starter_color=[random.randint(0,255) for i in range(3)]
app = dash.Dash(__name__)

btn_style = {
        'background-color': 'rgb(255,255,255)',
        'color': 'transparent',
        'margin': 'auto',
        'display': 'inline-block',
        'height': '40px',
        'width': '12%',
        'padding-top': '12%',
        'border': '1px',
        'margin-top': '1px',
        'margin-left': '1px'
        }

def get_led_style (device_id, led_id):
    color = backend.get_led_color(device_id, led_id)
    style = btn_style.copy()
    style['background-color'] = f"rgb({color[0]},{color[1]},{color[2]})"
    return style

def get_my_devices():
    backend.get_my_devices()
    return backend._my_device_ids

my_devices = get_my_devices()

if len(my_devices) <= 0:
    raise ValueError("No devices available for this user.")

header = html.H1(children=f"Group L1-G4")

subheader = html.H4(children=f"{firstname.capitalize()} {lastname.capitalize()}")

interval = dcc.Interval('interval',5000)

dropdown = html.Div([
    "Devices",
    dcc.Dropdown(
        id = 'dropdown_devices',
        options=[
            {'label': f"{backend.get_device_owner(id)} ({str(id)})",'value': str(id)} for id in my_devices
            ],
        value=my_devices[0]
        )
    ])

def build_led_buttons(deviceid):
    ledarray=[
        html.Div(
            children = [
                html.Button(
                    id = str((col+1)+row*8),
                    style = get_led_style(deviceid,(col+1)+row*8)) for col in range (8)
                ]
            ) for row in range(8)
        ]
    return ledarray

leds = html.Div(
    id = 'leddiv',
    children = build_led_buttons(my_devices[0]),
    style={'width': '100%', 'display': 'inline-block'}
    )

#callback to update leds whenever a new device is selected.
@app.callback(
    Output('leddiv','children'),
    Input('dropdown_devices','value'),
    prevent_initial_call=True,
    )
def update_leds(dropvalue):
    if dropvalue is not None:
        deviceid=dropvalue
    else:
        deviceid=my_devices[0]
    logger.debug(f"Device id is {deviceid}")
    return build_led_buttons(deviceid)

color_picker = daq.ColorPicker(
    id='color_picker',
    label='Pick a color',
    value=dict(
        rgb=dict(
            r=starter_color[0],
            g=starter_color[1],
            b=starter_color[2],
            a=1)
        ),
    size=500,
    )

#Register a callback for each led.
for ledn in range(64):
    @app.callback(Output(f"{str(ledn+1)}",'style'),
                  Input(f"{str(ledn+1)}",'n_clicks'),                  
                  State("color_picker","value"),
                  State('dropdown_devices','value'),
                  State(f"{str(ledn+1)}",'style'),
                  Input('interval','n_intervals'),
                  State(f"{str(ledn+1)}",'id'),
                  prevent_initial_call=True,
                  )
    def changebtn(nclicks, colorvalue, deviceid, style, ninterval, ledid):
        ctx = callback_context
        triggeredprop = [p['prop_id'] for p in ctx.triggered]
        if triggeredprop[0] != ".":
            triggeredprop=triggeredprop[0].split('.')
            # If the event was created from a click on a button, update the button style and the color in the database.
            if triggeredprop[1] == 'n_clicks':
                style['background-color'] = f"rgb({colorvalue['rgb']['r']},{colorvalue['rgb']['g']},{colorvalue['rgb']['b']})"
                try:
                    newcolor=[colorvalue['rgb']['r'],colorvalue['rgb']['g'],colorvalue['rgb']['b']]
                    logger.debug(f'Setting led status: ({deviceid}:{ledid}) = {newcolor}')
                    backend.set_led_status(
                        deviceid,
                        ledid,
                        newcolor,
                        )                    
                except Exception as e:
                    logger.debug(f"Error occurred while setting LED color...{newcolor} {e}")
                    logger.debug(traceback.format_exc())
            # if the event was triggered by the timer fetch all led colors from database.
            elif triggeredprop[1] == 'n_intervals':
                try:
                    dbcolor = backend.get_led_color(deviceid, ledid)
                    style['background-color'] = f"rgb({dbcolor[0]},{dbcolor[1]},{dbcolor[2]})"
                except Exception as e:
                    logger.debug(f"Error occurred while setting LED color.. {e}")
                    logger.error(traceback.format_exc())
        return style
    
body = [
    interval,
    header,
    subheader,
    dropdown,
    leds,
    color_picker,
    ]
        
app.layout = html.Div(children=body)

if __name__ == "__main__":
    app.run_server(debug=True, host='0.0.0.0', dev_tools_ui=False)
