ui = true
disable_mlock = true

storage "file" {
  path = "/vault/file"
}

listener "tcp" {
  address       = "0.0.0.0:8200"
  tls_cert_file = "/vault/certs/erag-local-vault-server.crt"
  tls_key_file  = "/vault/certs/erag-local-vault-server.key"
}

api_addr = "https://localhost:8200"