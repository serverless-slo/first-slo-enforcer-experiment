./setup-exp-without-slo.sh
# Run the SLO enforcer
cd faasslo
make run ENABLE_WEBHOOKS=false
cd ..


