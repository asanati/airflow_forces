import serial, time
import threading
import signal
import sys


class ForceGauge:
	START_WORD = b"\x02"
	END_WORD = b"\r"
	CONSTANT_g = 9.810
	def __init__(self, port="/dev/ttyUSB2", baudrate=9600):
		"""Initialize serial port to connect to force gauge"""
		self.serial = serial.Serial(port=port, baudrate=baudrate)

		self._byte_index = 0
		
		self.gauge_lock = threading.Lock()
		self.force_val = 0
		self.force_unit = None
		self.force_sign = 0
		self.force_decimal = 0
		self.force_raw = 0
		self.force_updated_time = 0

		self.exit_trigerred = threading.Event()
		self.update_state_thread = threading.Thread(target=self.update_state_loop)
		# self.update_state_freq = 50
		self.update_state_thread.start()

	def read_next_byte(self):
		"""Read and return data from gauge and handle errors"""
		new_byte = self.serial.read()
		return new_byte

	def update_state_loop(self):
		""""""
		while not self.exit_trigerred.is_set():
			try:
				self.update_gauge_state_machine()
			except ValueError as e:
				print(e)
			# time.sleep(1.0 / self.update_state_freq)

	def update_gauge_state_machine(self):
		new_byte = self.read_next_byte()
		# print(f"idx: {self._byte_index} --> {str(new_byte)}")

		# D15: Start Word
		if self._byte_index == 0:
			if new_byte == ForceGauge.START_WORD:
				self._byte_index += 1
			else:
				print(f"ERROR: Expected start word but received {str(new_byte)} instead")
				self._byte_index = 0

		# D14: expect '4'
		elif self._byte_index == 1:
			if new_byte == b"4":
				self._byte_index += 1	
			else:
				print(f"ERROR: Expected '4' but received {str(new_byte)} instead")
				self._byte_index = 0

		# D13: expect '1'
		elif self._byte_index == 2:
			if new_byte == b"1":
				self._byte_index += 1	
			else:
				print(f"ERROR: Expected '1' but received {str(new_byte)} instead")
				self._byte_index = 0
		
		# D12: expect '5'
		elif self._byte_index == 3:
			if new_byte == b"5":
				self._byte_index += 1	
			else:
				print(f"ERROR: Expected '5' but received {str(new_byte)} instead")
				self._byte_index = 0
		
		# D11: set unit of force 
		elif self._byte_index == 4:
			# set to kg
			if new_byte == b"5": 		
				self.force_unit = "kg"
				self._byte_index += 1	
			# set to LB
			elif new_byte == b"6": 		
				self.force_unit = "LB"
				self._byte_index += 1	
			# set to g
			elif new_byte == b"7": 		
				self.force_unit = "g"
				self._byte_index += 1	
			# set to oz
			elif new_byte == b"8": 		
				self.force_unit = "oz"
				self._byte_index += 1	
			# set to Newton
			elif new_byte == b"9": 		
				self.force_unit = "Newton"
				self._byte_index += 1				
			else:
				print(f"ERROR: Expected number btw 5-9 but received {str(new_byte)} instead")
				self._byte_index = 0

		# D10: set sign
		elif self._byte_index == 5:
			# Force has positive sign
			if new_byte == b"0":
				self.force_sign = 1
				self._byte_index += 1
			# Force has negative sign
			elif new_byte == b"1":
				self.force_sign = -1
				self._byte_index += 1					
			else:
				print(f"ERROR: Expected '0' or '1' but received {str(new_byte)} instead")
				self._byte_index = 0
		# D9: set decimal point (dp)
		elif self._byte_index == 6:
			# No dp
			floatingpoint_position = int(new_byte)
			if floatingpoint_position >= 0 and floatingpoint_position < 4:
				self.force_decimal = 10**(-floatingpoint_position)
				self._byte_index += 1
			else:
				print(f"ERROR: Expected number btw 0-3 but received {str(new_byte)} instead")
				self._byte_index = 0
			#D8 to D1 set raw force
		elif self._byte_index >= 7 and self._byte_index <15:
			self.force_raw = self.force_raw * 10
			self.force_raw += float(new_byte)
			self._byte_index += 1
		# D15: End Word
		elif self._byte_index == 15:
			if new_byte == ForceGauge.END_WORD:
				self._byte_index = 0
				with self.gauge_lock:
					self.force_val = self.force_raw * self.force_decimal * self.force_sign
					self.force_updated_time = time.time()
					self.force_raw = 0.0
					self.force_decimal = 0
					self.force_sign = 1
				# print(f"done reading bytes Force is: {self.force_val}")
			else:
				print(f"ERROR: Expected start word but received {str(new_byte)} instead")
				self._byte_index = 0

	def read_gauge(self):
		with self.gauge_lock:
			return self.force_val, self.force_unit, time.time() - self.force_updated_time

	def read_force(self):
		sensor_reading, unit, update_time = self.read_gauge()
		if unit == "g":
			return sensor_reading * ForceGauge.CONSTANT_g * 1e-3, update_time
		elif unit == "Newton":
			return sensor_reading, update_time
		elif unit == "kg":
			return sensor_reading * ForceGauge.CONSTANT_g, update_time
		else:
			# Sometimes the sensor take some time to initialize
			# and during this time the unit is set to None
			# Assume grams?
			# TODO(@gavin): Error handling
			return sensor_reading * ForceGauge.CONSTANT_g * 1e-3, update_time

	def signal_handler(self, sig, frame):
		self.exit_trigerred.set()
		self.update_state_thread.join()
		sys.exit(0)

if __name__ == "__main__":
	fg = ForceGauge()
	signal.signal(signal.SIGINT, fg.signal_handler)

	while not fg.exit_trigerred.is_set():
		try:
			# print(f"Force gauge reading: {fg.read_force()}")
			print(f"Force gauge reading: {fg.read_gauge()}")
			time.sleep(0.1)
		except NotImplementedError:
			print(f"Caught NotImplementedError")
			fg.exit_trigerred.set()
	fg.update_state_thread.join()
