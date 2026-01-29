from mido import get_input_names, get_output_names

print("Available MIDI input ports:")
for port in get_input_names():
    print(port)

print("Available MIDI output ports:")
for port in get_output_names():
    print(port)
