include config

init:
    #pip install -r requirements.txt
check-aws:
	#ToDo: check if aws exists, prompt to install it otherwise

build :
	rm -r dist
	mkdir dist
	@echo "Packaging dist-package ..."
	cd lambda-libs; zip -r -q ../dist/dist-package.zip *
	@echo "done."
	@echo "Packaging app ..."
	cd journey; zip -r -q ../dist/dist-package.zip *
	@echo "done."

deploy-direct-create : check-aws #build
	@echo "uploading code (this may take a while) ..."
	aws lambda create-function \
	--region $(LAMBDA_REGION) \
	--function-name $(LAMBDA_FUNCTION)  \
	--zip-file fileb://dist/dist-package.zip \
	--role $(LAMBDA_ROLE) \
	--handler $(LAMBDA_HANDLER) \
	--runtime python2.7 \
	--timeout 300 \
	--memory-size 1536 \
	--environment "Variables={$(LAMBDA_VARIABLES)}"
	@echo "done."
	@echo "Remember to set any triggers manually if needed."


deploy-direct-update : check-aws #build
	@echo "uploading code (this may take a while) ..."
	aws lambda update-function-code \
	--function-name $(LAMBDA_FUNCTION)  \
	--zip-file fileb://dist/dist-package.zip
	@echo "done."

s3-upload : check-aws
	@echo "uploading code (this may take a while) ..."
	aws s3 cp dist/dist-package.zip s3://$(LAMBDA_SRCBUCKET)/
	@echo "done."

deploy-s3-create : check-aws #build s3-upload
	@echo "uploading code (this may take a while) ..."
	aws lambda create-function \
	--region $(LAMBDA_REGION) \
	--function-name $(LAMBDA_FUNCTION)  \
	--code S3Bucket=$(LAMBDA_SRCBUCKET),S3Key=dist-package.zip \
	--role $(LAMBDA_ROLE) \
	--handler $(LAMBDA_HANDLER) \
	--runtime python2.7 \
	--timeout 300 \
	--memory-size 1536 \
	--environment "Variables={$(LAMBDA_VARIABLES)}"
	@echo "done."
	@echo "Remember to set any triggers manually if needed."


deploy-s3-update : check-aws build s3-upload
	@echo "updating function from bucket ..."
	aws lambda update-function-code --function-name $(LAMBDA_FUNCTION) --s3-bucket $(LAMBDA_SRCBUCKET) --s3-key dist-package.zip
	@echo "done."

delete-function : check-aws
	aws lambda delete-function --function-name $(LAMBDA_FUNCTION)

test-remote : check-aws
	@echo "invoking function ..."
	aws lambda invoke \
	--invocation-type RequestResponse \
	--function-name $(LAMBDA_FUNCTION) \
	--region $(LAMBDA_REGION) \
	--payload file://$(REMOTE_TESTEVENT) \
	--log Tail tests/output.txt
	@echo "done."

init-test-local:
	@echo "creating testenv ..."
	pip install virtualenv
	rm -rf testenv
	virtualenv testenv/ --python=python2.7 --no-site-packages
	mkdir testenv/results
	. testenv/bin/activate ; \
	python testenv/bin/pip install python-lambda-local ; \
	python testenv/bin/pip install -r requirements.txt ; \
	deactivate

get-testdata:
	@if [ ! -d "testdata" ]; then \
		echo "downloading testdata (this may take a while) ..." ; \
		mkdir testdata ; \
		aws s3 sync s3://$(LAMBDA_TESTDATA) testdata; \
	fi

test-local:
	@if [ ! -d "testenv" ]; then echo "testenv folder does not exist. Please run 'make init-test-local' first."; false; fi
	@if [ ! -d "testdata" ]; then echo "testdata folder does not exist. Please run 'make get-testdata' first."; false; fi
	. testenv/bin/activate ; \
	export $(subst ;,,$(LOCAL_VARIABLES)) ; \
	python testenv/bin/python-lambda-local -l lib/ -f $(LOCAL_HANDLER) -t 30000 $(LOCAL_APP) $(LOCAL_TESTEVENT) ; \
	deactivate

run-tests:
	py.test tests

.PHONY: init run-tests
