import pyaudio

p = pyaudio.PyAudio()

print("\n=== Listando Dispositivos de Áudio ===")
info = p.get_host_api_info_by_index(0)
numdevices = info.get('deviceCount')

input_devices = []
for i in range(0, numdevices):
    if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
        dev_name = p.get_device_info_by_host_api_device_index(0, i).get('name')
        input_devices.append((i, dev_name))
        print(f"ID {i}: {dev_name}")

print("\n=== Testando Abertura de Stream (16kHz, Mono) ===")
working_device = None

for dev_id, dev_name in input_devices:
    print(f"Testando ID {dev_id} ({dev_name})...", end=" ")
    try:
        stream = p.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=16000,
                        input=True,
                        input_device_index=dev_id,
                        frames_per_buffer=4096)
        stream.stop_stream()
        stream.close()
        print("OK!")
        if working_device is None:
            working_device = dev_id
    except Exception as e:
        print(f"FALHA: {e}")

p.terminate()

if working_device is not None:
    print(f"\n[SUCESSO] O dispositivo ID {working_device} parece funcional.")
else:
    print("\n[ERRO] Nenhum dispositivo suportou as configurações necessárias (16kHz Mono).")
