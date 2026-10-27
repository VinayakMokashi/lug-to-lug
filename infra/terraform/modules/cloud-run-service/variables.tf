variable "name" {
  description = "Cloud Run service name, for example api-staging."
  type        = string
}

variable "region" {
  description = "Cloud Run region."
  type        = string
}

variable "service_account" {
  description = "Email of the service account the service runs as."
  type        = string
}

variable "env" {
  description = "Plain environment variables. Secrets come from Secret Manager, never from here."
  type        = map(string)
  default     = {}
}

variable "memory" {
  description = "Memory limit per instance."
  type        = string
  default     = "512Mi"
}

variable "max_instances" {
  description = "Upper bound on instances, which caps the cost of a traffic spike."
  type        = number
  default     = 2
}

variable "concurrency" {
  description = "Requests one instance handles at once."
  type        = number
  default     = 80
}

variable "timeout_seconds" {
  description = "Request timeout."
  type        = number
  default     = 60
}

variable "public" {
  description = "Whether anyone may call the service without signing in."
  type        = bool
  default     = true
}

variable "deletion_protection" {
  description = "Refuse terraform destroy. Off for staging, on for production."
  type        = bool
  default     = false
}
