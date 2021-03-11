DOCKER_IMAGE = jenkins_exporter
VENV_DIR = venv_jenkins_exporter

venv:
	@echo "Creating VirtualEnv on directory ${VENV_DIR}.."
	@echo " "

	pip install virtualenv
	python -m venv ${VENV_DIR}
	mkdir -p ${VENV_DIR}/src
	
	# Activate venv and install dependencies
	. ${VENV_DIR}/bin/activate && pip install -r requirements.txt

	@echo "You can activate virtualenv with 'source ${VENV_DIR}/bin/activate'"

docker:
	@echo "Building docker image..."
	@echo " "

	docker build -t ${DOCKER_IMAGE}:latest .

tests: venv
	@echo "Running Tests..."

	# Activate venv and install dependencies and run tests
	. ${VENV_DIR}/bin/activate && pip install -r requirements-tests.txt && python -m unittest tests.py