terraform {
  required_version = ">= 1.6.0"

  required_providers {
    mgc = {
      source  = "magalucloud/mgc"
      version = ">= 0.50.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
  }
}

provider "mgc" {
  api_key = var.mgc_api_key
  region  = var.region
}
