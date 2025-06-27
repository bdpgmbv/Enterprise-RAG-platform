CA := docker/certs/erag-local-root-ca.crt
VAULT := https://localhost:8200

.PHONY: unseal

unseal:
	@for i in 0 1 2; do \
	  curl -s --cacert $(CA) -X PUT $(VAULT)/v1/sys/unseal \
	    -d "{\"key\":\"$$(python3 -c "import json;print(json.load(open('vault-init.json'))['keys_base64'][$$i])")\"}" > /dev/null; \
	done
	@curl -s --cacert $(CA) $(VAULT)/v1/sys/health